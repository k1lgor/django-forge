"""Post-generation shell command runner.

Runs ``uv sync``, ``makemigrations``, ``migrate``, and
``check --deploy`` in the scaffolded project directory.
"""

import shutil
import subprocess
from pathlib import Path

from django_forge.cli.console import console


def run_post_install(project_dir: Path) -> bool:
    """Run post-generation steps in *project_dir*.

    Steps:
    1. ``uv sync`` — install dependencies
    2. ``uv run manage.py makemigrations`` — create initial migrations
    3. ``uv run manage.py migrate`` — apply initial migrations
    4. ``uv run manage.py check --deploy`` — verify deployment readiness

    Each step is skipped if the previous step failed.

    Args:
        project_dir: Absolute path to the generated project.

    Returns:
        ``True`` if all steps succeeded, ``False`` otherwise.
    """
    project_name = project_dir.name

    if not _check_uv_installed(project_name):
        return False

    if not _run_uv_sync(project_dir):
        return False

    if not _run_makemigrations(project_dir):
        return False

    if not _run_migrate(project_dir):
        return False

    _run_check_deploy(project_dir)
    return True


def _check_uv_installed(project_name: str) -> bool:
    """Check if ``uv`` is available on PATH.

    Prints installation instructions if not found.
    """
    if shutil.which("uv") is not None:
        return True

    console.print()
    console.print("[forge.error]X uv not found.[/]")
    console.print()
    msg = (
        "  django-forge requires [forge.highlight]uv[/]"
        " to install project dependencies."
    )
    console.print(msg)
    console.print()
    console.print("  [forge.label]Install uv:[/]")
    console.print(
        "    [forge.highlight]curl -LsSf"
        " https://astral.sh/uv/install.sh | sh[/]"
        "      [forge.muted]# macOS / Linux[/]"
    )
    console.print(
        '    [forge.highlight]powershell -c'
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
    console.print(
        f"    [forge.highlight]cd {project_name} && uv sync[/]"
    )
    console.print()
    console.print(
        "  [forge.muted]All project files were written."
        " Only dependency installation failed.[/]"
    )
    return False


def _run_uv_sync(project_dir: Path) -> bool:
    """Run ``uv sync`` in *project_dir*.

    Returns ``True`` on success, ``False`` on failure.
    """
    console.print()
    console.print(
        "  [forge.label]Installing dependencies...[/]"
        " [forge.muted](this may take a moment)[/]"
    )

    returncode, _stdout, stderr = _run_cmd(
        ["uv", "sync"], cwd=project_dir
    )

    if returncode != 0:
        console.print(
            "[forge.error]X Dependency installation failed.[/]"
        )
        console.print(
            f"  [forge.muted]Error: {_truncate(stderr, 300)}[/]"
        )
        console.print()
        console.print(
            "  [forge.info]Try running:[/]"
            f" [forge.highlight]cd {project_dir.name}"
            " && uv sync[/]"
        )
        return False

    console.print("  [forge.success]Dependencies installed[/]")
    return True


def _run_makemigrations(project_dir: Path) -> bool:
    """Create initial migrations for the custom User model.

    Runs ``uv run manage.py makemigrations accounts``
    — explicit app label ensures migrations are created
    even when no migrations directory exists yet.
    """
    returncode, _stdout, stderr = _run_cmd(
        ["uv", "run", "manage.py", "makemigrations", "accounts"],
        cwd=project_dir,
    )

    if returncode != 0:
        console.print(" [forge.error]X[/]")
        console.print(
            "[forge.error]X Migration creation failed.[/]"
        )
        console.print(
            f"  [forge.muted]Error: {_truncate(stderr, 300)}[/]"
        )
        console.print()
        console.print(
            "  [forge.info]Try running:[/]"
            f" [forge.highlight]cd {project_dir.name}"
            " && uv run manage.py makemigrations[/]"
        )
        return False
    return True


def _run_migrate(project_dir: Path) -> bool:
    """Run ``uv run manage.py migrate`` in *project_dir*.

    Returns ``True`` on success, ``False`` on failure.
    """
    console.print(
        "  [forge.label]Setting up database...[/]", end=""
    )

    returncode, _stdout, stderr = _run_cmd(
        ["uv", "run", "manage.py", "migrate"], cwd=project_dir
    )

    if returncode != 0:
        console.print(" [forge.error]X[/]")
        console.print(
            "[forge.error]X Database setup failed.[/]"
        )
        console.print(
            f"  [forge.muted]Error: {_truncate(stderr, 300)}[/]"
        )
        console.print()
        console.print(
            "  [forge.info]This is likely a database"
            " configuration issue.[/]"
        )
        console.print(
            "  [forge.info]Check your [forge.highlight].env[/]"
            f" file at [forge.highlight]{project_dir.name}/.env[/]"
        )
        return False

    console.print(" [forge.success]done[/]")
    return True


def _run_check_deploy(project_dir: Path) -> bool:
    """Run ``uv run manage.py check --deploy``.

    Warnings are non-blocking — we print them but don't fail.
    """
    console.print(
        "  [forge.label]Deployment check...[/]", end=""
    )

    returncode, _stdout, stderr = _run_cmd(
        ["uv", "run", "manage.py", "check", "--deploy"],
        cwd=project_dir,
    )

    if returncode != 0:
        console.print(" [forge.warning]warning[/]")
        console.print(
            "[forge.warning]Deployment check found"
            " issues (non-blocking):[/]"
        )
        for line in stderr.splitlines():
            console.print(f"  [forge.muted]{line}[/]")
        console.print()
        console.print(
            "  [forge.info]Review [forge.highlight]"
            "config/settings/base.py[/] before deploying.[/]"
        )
        return True  # non-blocking

    console.print(" [forge.success]ok[/]")
    return True


def _run_cmd(
    cmd: list[str], cwd: Path
) -> tuple[int, str, str]:
    """Run a shell command and return
    ``(returncode, stdout, stderr)``.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 300 seconds"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)


def _truncate(text: str, max_len: int = 300) -> str:
    """Truncate text, appending ``...`` if truncated."""
    if len(text) <= max_len:
        return text
    cutoff = text[:max_len].rsplit("\n", 1)[0]
    return cutoff + "\n..."
