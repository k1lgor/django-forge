"""Scaffold orchestration for ``forge start``.

Replaces the stub from Story 1.1 with the full pipeline:
prompt -> render -> install -> success.
"""

import re
import secrets
import subprocess
import sys
from pathlib import Path

from django_forge import __version__
from django_forge.cli.console import console
from django_forge.cli.installer import run_post_install
from django_forge.cli.prefs import save_prefs
from django_forge.cli.prompts import confirm_scaffold
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


def start_project(*, project_name: str, no_input: bool = False) -> None:
    """Scaffold a new Django project.

    Full end-to-end flow:
    1. Detect CI/no-input mode
    2. Brand banner
    3. Validate project name
    4. Check target directory
    5. Confirm scaffold settings with user
    6. Generate template files via renderer
    7. Install dependencies, migrate, deploy-check
    8. Print success banner with next steps
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
        return

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
            return
        if not _handle_existing_directory(target_dir):
            return

    # 4. Confirm scaffold settings
    secret_key = _generate_secret_key()
    context = confirm_scaffold(
        project_name,
        api=None,
        db=None,
        layers=None,
        no_input=no_input,
    )
    if context is None:
        return
    context["secret_key"] = secret_key

    save_prefs(api=context["api"], db=context["db"], layers=context["layers"])

    # 4. Generate template files
    renderer = _get_renderer()
    console.print()
    console.print(f"  [forge.label]Forging [forge.highlight]{project_name}[/]...")
    renderer.render_project(context, target_dir)

    # 5. Post-install steps
    success = run_post_install(target_dir)

    # 6. Offer to create a superuser (skip in CI / --no-input)
    if success and not no_input:
        _prompt_createsuperuser(target_dir)

    # 7. Success banner
    if success:
        _print_success(project_name)


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
    """Generate a Django-style secret key."""
    key = secrets.token_urlsafe(50)
    return f"django-insecure-{key}"


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
    console.print("  [forge.label]Set production environment variables:[/]")
    console.print("    [forge.highlight]cp .env.example .env[/]")
    console.print("    [forge.muted](edit .env with your secrets)[/]")
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
