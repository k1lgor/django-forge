"""Post-generation shell command runner.

Runs ``uv sync``, ``makemigrations``, ``migrate`` and
``check --deploy`` in the scaffolded project directory.

Failed subprocesses keep their full stdout/stderr in
``<project>/.forge-logs/<command>-<timestamp>.log`` (one file per run,
URL credentials redacted, never uploaded) and the error banner prints that
path; ``--verbose`` mirrors the same output live instead (G7).
"""

import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import typer

from django_forge.cli.console import console

_VERBOSE = False

# Deploy-check ids that fail the run: DEBUG enabled in production and an
# insecure or weak SECRET_KEY (or fallback). Everything else — including the
# proxy-dependent warnings — becomes a printed pre-deploy checklist (G4).
_BLOCKING_CHECK_IDS = frozenset({"security.W009", "security.W018", "security.W025"})
_CHECK_ISSUE_RE = re.compile(r"^\s*([a-z_]+\.[EW]\d+):\s*(.*?)\s*$")
_CREDENTIAL_RE = re.compile(r"://[^/\s:@]+:[^/\s@]*@")

_CMD_TIMEOUT = 300


def set_verbose(value: bool) -> None:
    """Turn live subprocess mirroring on/off (set from the app callback)."""
    global _VERBOSE
    _VERBOSE = bool(value)


def is_verbose() -> bool:
    """Whether ``--verbose`` was requested."""
    return _VERBOSE


def run_post_install(project_dir: Path) -> bool:
    """Run post-generation steps in *project_dir*.

    Steps:
    1. ``uv sync`` — install dependencies (the ``dev`` dependency group is
       installed by a plain sync, no ``--extra`` flags)
    2. ``uv run manage.py makemigrations accounts`` — create initial migrations
    3. ``uv run manage.py migrate`` — apply initial migrations
    4. ``uv run manage.py check --deploy --settings=config.settings.prod`` —
       deployment readiness with fail-level classification

    Each step is skipped if the previous step failed, so one run produces at
    most one failure log — the timestamp is generated once per run.

    Args:
        project_dir: Absolute path to the generated project.

    Returns:
        ``True`` if all steps succeeded, ``False`` otherwise.

    Raises:
        typer.Exit: With code 1 when ``uv`` is not installed.
    """
    project_name = project_dir.name

    if not _check_uv_installed(project_name):
        raise typer.Exit(code=1)

    stamp = _timestamp()

    if not _run_uv_sync(project_dir, stamp=stamp):
        return False
    if not _run_makemigrations(project_dir, stamp=stamp):
        return False
    if not _run_migrate(project_dir, stamp=stamp):
        return False
    return _run_check_deploy(project_dir, stamp=stamp)


def _check_uv_installed(project_name: str) -> bool:
    """Check if ``uv`` is available on PATH.

    Prints installation instructions if not found.
    """
    if shutil.which("uv") is not None:
        return True

    console.print()
    console.print("[forge.error]X uv not found.[/]")
    console.print()
    msg = "  django-forge requires [forge.highlight]uv[/] to install project dependencies."
    console.print(msg)
    console.print()
    console.print("  [forge.label]Install uv:[/]")
    console.print(
        "    [forge.highlight]curl -LsSf"
        " https://astral.sh/uv/install.sh | sh[/]"
        "      [forge.muted]# macOS / Linux[/]"
    )
    console.print(
        "    [forge.highlight]powershell -c"
        ' "irm https://astral.sh/uv/install.ps1 | iex"[/]'
        "   [forge.muted]# Windows[/]"
    )
    console.print(
        "    [forge.highlight]brew install uv[/]"
        "                                                [forge.muted]"
        "# Homebrew[/]"
    )
    console.print()
    console.print("  [forge.info]After installing uv, run:[/]")
    console.print(f"    [forge.highlight]cd {project_name} && uv sync[/]")
    console.print()
    console.print(
        "  [forge.muted]All project files were written. Only dependency installation failed.[/]"
    )
    return False


def _run_uv_sync(project_dir: Path, *, stamp: str | None = None) -> bool:
    """Run ``uv sync`` in *project_dir*.

    A plain sync installs the ``dev`` dependency group too (G5), so no
    ``--extra``/``--all-extras`` flag is used.

    Returns ``True`` on success, ``False`` on failure.
    """
    console.print()
    console.print(
        "  [forge.label]Installing dependencies...[/] [forge.muted](this may take a moment)[/]"
    )

    returncode, output, log_path = _run_cmd(
        ["uv", "sync"], cwd=project_dir, log_name="uv-sync", stamp=stamp
    )

    if returncode != 0:
        console.print("[forge.error]X Dependency installation failed.[/]")
        _print_failure_detail(output, log_path)
        console.print()
        console.print(
            f"  [forge.info]Try running:[/] [forge.highlight]cd {project_dir.name} && uv sync[/]"
        )
        return False

    console.print("  [forge.success]Dependencies installed[/]")
    return True


def _run_makemigrations(project_dir: Path, *, stamp: str | None = None) -> bool:
    """Create initial migrations for the custom User model.

    Runs ``uv run manage.py makemigrations accounts``
    — explicit app label ensures migrations are created
    even when no migrations directory exists yet.
    """
    returncode, output, log_path = _run_cmd(
        ["uv", "run", "manage.py", "makemigrations", "accounts"],
        cwd=project_dir,
        log_name="makemigrations",
        stamp=stamp,
    )

    if returncode != 0:
        console.print("[forge.error]X Migration creation failed.[/]")
        _print_failure_detail(output, log_path)
        console.print()
        console.print(
            "  [forge.info]Try running:[/]"
            f" [forge.highlight]cd {project_dir.name}"
            " && uv run manage.py makemigrations[/]"
        )
        return False
    console.print("  [forge.success]Migrations created[/]")
    return True


def _run_migrate(project_dir: Path, *, stamp: str | None = None) -> bool:
    """Run ``uv run manage.py migrate`` in *project_dir*.

    Returns ``True`` on success, ``False`` on failure.
    """
    console.print("  [forge.label]Setting up database...[/]", end="")

    returncode, output, log_path = _run_cmd(
        ["uv", "run", "manage.py", "migrate"],
        cwd=project_dir,
        log_name="migrate",
        stamp=stamp,
    )
    if returncode != 0:
        console.print(" [forge.error]X[/]")
        console.print("[forge.error]X Database setup failed.[/]")
        _print_failure_detail(output, log_path)
        console.print()
        console.print("  [forge.info]This is likely a database configuration issue.[/]")
        console.print(
            "  [forge.info]Check your [forge.highlight].env[/]"
            f" file at [forge.highlight]{project_dir.name}/.env[/]"
        )
        return False

    console.print(" [forge.success]done[/]")
    return True


def _run_check_deploy(project_dir: Path, *, stamp: str | None = None) -> bool:
    """Run ``check --deploy`` against ``config.settings.prod`` (decision 1).

    Fail-level classification: ``DEBUG = True`` (``security.W018``) and an
    insecure ``SECRET_KEY`` (``security.W009``/``W025``) fail the run, as do
    check errors and crashes; every other warning — including the
    proxy-dependent ones — is printed as a pre-deploy checklist instead of
    failing the command (G4).
    """
    console.print("  [forge.label]Deployment check...[/]", end="")

    returncode, output, log_path = _run_cmd(
        ["uv", "run", "manage.py", "check", "--deploy", "--settings=config.settings.prod"],
        cwd=project_dir,
        log_name="check-deploy",
        stamp=stamp,
    )

    issues = _parse_check_issues(output)
    blocking = [issue for issue in issues if _is_blocking_issue(issue[0])]
    checklist = [issue for issue in issues if not _is_blocking_issue(issue[0])]

    if returncode != 0 or blocking:
        console.print(" [forge.error]X[/]")
        console.print("[forge.error]Deployment check failed:[/]")
        shown = blocking or issues
        for check_id, message in shown:
            console.print(f"  [forge.error]{check_id}:[/]", end=" ")
            console.print(message, markup=False, soft_wrap=True)
        if not shown and output:
            console.print("  [forge.muted]Last output:[/]")
            console.print(_truncate(output.strip(), 300), markup=False, soft_wrap=True)
        if log_path is not None:
            console.print(f"  [forge.muted]Full output:[/] [forge.highlight]{log_path}[/]")
        console.print()
        console.print(
            "  [forge.info]Fix the report above, then re-run:[/] "
            f"[forge.highlight]cd {project_dir.name} && uv run manage.py check"
            " --deploy --settings=config.settings.prod[/]"
        )
        console.print()
        return False

    if checklist:
        console.print(" [forge.warning]checklist[/]")
        console.print("[forge.warning]Pre-deploy checklist (review before shipping):[/]")
        for check_id, message in checklist:
            console.print(f"  [forge.muted]☐ {check_id}:[/]", end=" ")
            console.print(message, markup=False, soft_wrap=True)
        console.print()
        return True

    console.print(" [forge.success]ok[/]")
    return True


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    *,
    log_name: str,
    stamp: str | None = None,
) -> tuple[int, str, Path | None]:
    """Run *cmd* in *cwd* and return ``(returncode, output, log_path)``.

    stdout and stderr are merged into ``output``. With ``--verbose`` the
    lines are mirrored live as they arrive; otherwise they are buffered and —
    on failure only — written in full to
    ``<cwd>/.forge-logs/<log_name>-<timestamp>.log`` with URL credentials
    redacted before writing. ``log_path`` is ``None`` when the command
    succeeded or the log could not be written (nothing is ever uploaded).
    """
    cwd = Path(cwd)
    if not cwd.is_dir():
        return 1, f"Working directory not found: {cwd}", None

    verbose = is_verbose()
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
    except FileNotFoundError:
        return 1, f"Command not found: {cmd[0]}", None
    except OSError as exc:
        return 1, str(exc), None

    lines: list[str] = []
    started = threading.Event()

    def _pump() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if verbose:
                if not started.is_set():
                    # End any pending status label before live output.
                    console.print()
                    started.set()
                console.print(line, end="", markup=False, highlight=False, soft_wrap=True)

    reader = threading.Thread(target=_pump, name="forge-cmd-output", daemon=True)
    reader.start()

    timed_out = False
    try:
        returncode = proc.wait(timeout=_CMD_TIMEOUT)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        returncode = proc.wait()
    reader.join(timeout=30)

    if timed_out:
        lines.append(f"\nCommand timed out after {_CMD_TIMEOUT} seconds\n")
    output = "".join(lines)
    if returncode == 0:
        return returncode, output, None
    return returncode, output, _write_failure_log(cwd, log_name, stamp, output)


def _write_failure_log(
    project_dir: Path,
    log_name: str,
    stamp: str | None,
    output: str,
) -> Path | None:
    """Write the full, redacted output of a failed command to the log dir."""
    try:
        log_dir = project_dir / ".forge-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        when = stamp or _timestamp()
        path = log_dir / f"{log_name}-{when}.log"
        path.write_text(_redact_credentials(output), encoding="utf-8")
    except OSError:
        return None
    return path


def _redact_credentials(text: str) -> str:
    """Replace ``://user:pass@`` with ``://<redacted>@`` before writing a log."""
    return _CREDENTIAL_RE.sub("://<redacted>@", text)


def _timestamp() -> str:
    """Local timestamp with seconds, e.g. ``20261104-101530``."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _print_failure_detail(output: str, log_path: Path | None) -> None:
    """Point at the full-output log instead of truncating stderr to 300 chars."""
    if log_path is not None:
        console.print(f"  [forge.muted]Full output:[/] [forge.highlight]{log_path}[/]")
        return
    console.print("  [forge.muted]Error:[/]", end=" ")
    console.print(_truncate(output.strip(), 300), markup=False, soft_wrap=True)


def _parse_check_issues(output: str) -> list[tuple[str, str]]:
    """Extract ``(check_id, message)`` pairs (with their HINT lines)."""
    issues: list[list[str]] = []
    for line in output.splitlines():
        match = _CHECK_ISSUE_RE.match(line)
        if match:
            issues.append([match.group(1), match.group(2)])
            continue
        hint = line.strip()
        if issues and hint.startswith("HINT:"):
            issues[-1][1] = f"{issues[-1][1]} ({hint.removeprefix('HINT:').strip()})"
    return [(check_id, message) for check_id, message in issues]


def _is_blocking_issue(check_id: str) -> bool:
    """``True`` for the deploy-check ids that fail the run (see module doc)."""
    if check_id in _BLOCKING_CHECK_IDS:
        return True
    return not check_id.rsplit(".", 1)[-1].startswith("W")


def _truncate(text: str, max_len: int = 300) -> str:
    """Truncate text, appending ``...`` if truncated."""
    if len(text) <= max_len:
        return text
    cutoff = text[:max_len].rsplit("\n", 1)[0]
    return cutoff + "\n..."
