"""Scaffold orchestration for ``forge-django start``.

Full pipeline: validate -> resolve settings -> render -> write ``.env`` ->
install -> success. Every failure branch raises ``typer.Exit(code=1)`` (G7).
"""

import re
import secrets
import subprocess
import sys
from pathlib import Path

import typer

from django_forge import __version__
from django_forge.cli.console import console
from django_forge.cli.installer import is_verbose, run_post_install
from django_forge.cli.prefs import save_prefs
from django_forge.cli.prompts import confirm_scaffold
from django_forge.project import build_context
from django_forge.renderer import Renderer

_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_BAD_NAME_PART = re.compile(r"[\\/]|\.\.|^\.|\{\{|\{%|[\x00-\x1f\x7f]")


def validate_project_name(name: str) -> str | None:
    """Return an error message if *name* is unsafe, else ``None``.

    Rejects path separators, ``..`` escapes, leading dots, Jinja2
    delimiters, and control characters so a hostile project name can
    never escape the working directory or inject into templates.
    """
    if not name:
        return "Project name cannot be empty."
    if _BAD_NAME_PART.search(name):
        return (
            "Project name contains invalid characters. Use letters, digits, "
            "dots, underscores, and hyphens only."
        )
    if not _PROJECT_NAME_RE.match(name):
        return (
            "Project name must start with a letter or digit and contain only "
            "letters, digits, dots, underscores, or hyphens."
        )
    return None


def start_project(
    *,
    project_name: str,
    no_input: bool = False,
    api: str | None = None,
    db: str | None = None,
    layers: list[str] | None = None,
) -> None:
    """Scaffold a new Django project.

    Full end-to-end flow:
    1. Detect CI/no-input mode
    2. Brand banner
    3. Validate project name
    4. Check target directory
    5. Resolve scaffold settings — the wizard interactively (prefs cache
       read/written), or Decision 2's fixed ``--no-input`` defaults
       (DRF + PostgreSQL + no layers) with explicit ``--api``/``--db``/
       ``--layers`` overrides, in which case the prefs cache is never
       touched
    6. Render template files, then write the generated ``SECRET_KEY`` into
       the gitignored ``.env`` (``.env.example`` keeps its placeholder, G8)
    7. Install dependencies, migrate, deploy-check against prod settings
    8. Print success banner with next steps

    Every failure branch raises ``typer.Exit(code=1)``; a user declining
    the summary simply aborts with status 0.
    """
    # 0. Detect CI / no-input mode
    ci_detected = False
    if not no_input and _is_ci_env():
        ci_detected = True
        no_input = True

    # 1. Brand banner
    _print_banner(project_name, no_input=no_input, ci_detected=ci_detected)

    # 2. Validate project name before touching the filesystem
    name_error = validate_project_name(project_name)
    if name_error:
        console.print()
        console.print(f"  [forge.error]{name_error}[/]")
        raise typer.Exit(code=1)

    # 3. Check target directory
    target_dir = Path.cwd() / project_name
    if target_dir.exists():
        if no_input:
            console.print()
            console.print(
                f"  [forge.error]Directory [forge.highlight]{project_name}[/] already exists.[/]"
            )
            console.print(
                "  [forge.muted]"
                "Refusing to overwrite in --no-input mode. Remove the "
                "directory manually or run interactively."
                "[/]"
            )
            raise typer.Exit(code=1)
        if not _handle_existing_directory(target_dir):
            raise typer.Exit(code=1)

    # 4. Resolve scaffold settings
    secret_key = _generate_secret_key()
    if no_input:
        # Decision 2: fixed defaults with explicit option overrides, and
        # the prefs cache is neither read nor written in this mode — so the
        # wizard (the prefs reader) is bypassed entirely.
        context = build_context(
            {"project_name": project_name, "api": api, "db": db, "layers": layers}
        )
    else:
        context = confirm_scaffold(
            project_name,
            api=api,
            db=db,
            layers=layers,
            no_input=no_input,
        )
        if context is None:
            # The user declined the summary: an abort, not a failure.
            return
        save_prefs(api=context["api"], db=context["db"], layers=context["layers"])
    context["secret_key"] = secret_key

    # 5. Generate template files
    renderer = _get_renderer()
    console.print()
    console.print(f"  [forge.label]Forging [forge.highlight]{project_name}[/]...")
    try:
        renderer.render_project(context, target_dir)
    except Exception as exc:  # every render failure exits 1 (G7)
        console.print()
        console.print(f"  [forge.error]Rendering failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    # The real key lives only in the gitignored `.env`; `.env.example` was
    # rendered from the `***` placeholder path (G8).
    _write_env_file(target_dir, secret_key)

    if is_verbose():
        console.print(
            f"  [forge.muted]verbose: api={context['api']} db={context['db']}"
            f" layers={', '.join(context['layers']) or 'none'}[/]"
        )
        console.print(f"  [forge.muted]verbose: secrets in {target_dir / '.env'} (gitignored)[/]")

    # 6. Post-install steps
    success = run_post_install(target_dir)

    # 7. Offer to create a superuser (skip in CI / --no-input)
    if success and not no_input:
        _prompt_createsuperuser(target_dir)

    # 8. Success banner — or a failing exit status when any step failed (G7)
    if not success:
        raise typer.Exit(code=1)
    _print_success(project_name)


def _write_env_file(project_dir: Path, secret_key: str) -> None:
    """Materialise ``.env`` from ``.env.example``, substituting the real key (G8).

    The example keeps its ``***`` placeholder; the generated key exists only
    here, where ``.gitignore`` excludes it from version control. Copying the
    example wholesale keeps every other scaffolded variable (DATABASE_URL,
    CORS_ALLOWED_ORIGINS, ...) available to the post-install steps without a
    manual copy step.
    """
    example = project_dir / ".env.example"
    try:
        if example.exists():
            content, count = re.subn(
                r"^DJANGO_SECRET_KEY=.*$",
                f"DJANGO_SECRET_KEY={secret_key}",
                example.read_text(encoding="utf-8"),
                count=1,
                flags=re.MULTILINE,
            )
            if not count:
                content = f"DJANGO_SECRET_KEY={secret_key}\n" + content
        else:  # pragma: no cover - example always renders
            content = f"DJANGO_SECRET_KEY={secret_key}\n"
        (project_dir / ".env").write_text(content, encoding="utf-8")
    except OSError as exc:
        console.print()
        console.print(f"  [forge.error]Cannot write .env:[/] {exc}")
        raise typer.Exit(code=1) from exc


def _print_banner(
    project_name: str,
    no_input: bool = False,
    ci_detected: bool = False,
) -> None:
    """Print the forge brand banner."""
    console.print()
    banner = "[forge.brand]"
    banner += f"=== FORGE v{__version__} - django project scaffolder ==="
    banner += "[/]"
    console.print(banner)
    console.print()
    console.print(
        f"  [forge.label]Forge your Django project:[/]  [forge.highlight]{project_name}[/]"
    )
    if no_input:
        console.print()
        if ci_detected:
            console.print("  [forge.info]CI mode detected - using defaults[/]")
        else:
            console.print("  [forge.info]Using defaults (--no-input mode)[/]")


def _handle_existing_directory(target_dir: Path) -> bool:
    """Prompt user about overwriting an existing directory.

    Returns ``True`` if the caller should continue (directory cleared),
    ``False`` if the user chose to abort.
    """
    import shutil

    console.print()
    console.print(
        f"  [forge.warning]Directory [forge.highlight]{target_dir.name}[/] already exists[/]"
    )
    console.print()

    try:
        response = input("  Overwrite? [y/N] ").strip().lower()
    except EOFError:
        response = ""
    if response not in ("y", "yes"):
        console.print("  [forge.muted]Aborted. No files were changed.[/]")
        return False

    shutil.rmtree(target_dir)
    console.print("  [forge.success]Directory cleared.[/]")
    return True


def _generate_secret_key() -> str:
    """Generate a Django-style secret key.

    Deliberately *not* prefixed ``django-insecure-``: Django's deploy check
    (``security.W009``) flags that prefix as insecure, and file 33 makes an
    insecure ``SECRET_KEY`` fail the post-install deploy check — a healthy
    scaffold must still exit 0 (CUJ 1).
    """
    return secrets.token_urlsafe(50)


def _get_renderer() -> Renderer:
    """Get a Renderer pointing to the embedded template tree."""
    template_root = Path(__file__).resolve().parent.parent / "templates"
    return Renderer(template_root)


def _print_success(project_name: str) -> None:
    """Print the success banner with next steps."""
    console.print()
    console.print("[forge.separator]-----------------------[/]")
    console.print()
    console.print("  [forge.success]Project forged successfully![/]")
    console.print()
    console.print("  [forge.label]Next steps:[/]")
    console.print(f"    [forge.highlight]cd {project_name}[/]")
    console.print("    [forge.highlight]uv run manage.py runserver[/]")
    console.print()
    console.print("  [forge.label]Environment:[/]")
    console.print(
        "    [forge.muted].env was created with a generated secret key — extend it as needed[/]"
    )
    console.print("    [forge.muted](every available variable is listed in .env.example)[/]")
    console.print()


def _is_ci_env() -> bool:
    """Detect if running in a CI environment."""
    import os

    return (
        os.environ.get("CI", "").lower() == "true"
        or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    )


def _prompt_createsuperuser(project_dir: Path) -> None:
    """Offer to create a Django superuser account interactively.

    Skips if stdin is not a TTY (piped input, CI, tests) or the
    user declines. The ``createsuperuser`` command runs in the
    foreground so the user can type their email and password directly.
    """
    if not sys.stdin.isatty():
        console.print()
        console.print("  [forge.muted]Non-interactive environment — skipping createsuperuser.[/]")
        console.print()
        return

    console.print()
    response = input("  Create a superuser account? [y/N] ").strip().lower()
    if response not in ("y", "yes"):
        console.print("  [forge.muted]Skipped. You can create one later with:[/]")
        console.print(
            f"    [forge.highlight]cd {project_dir.name} && uv run manage.py createsuperuser[/]"
        )
        console.print()
        return

    console.print()
    console.print("  [forge.label]Running [forge.highlight]createsuperuser[/]...")
    console.print()
    try:
        subprocess.run(
            ["uv", "run", "manage.py", "createsuperuser"],
            cwd=str(project_dir),
            check=False,
        )
    except FileNotFoundError:
        console.print("  [forge.error]uv not found — cannot run createsuperuser.[/]")
    console.print()
