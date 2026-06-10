"""Scaffold orchestration for ``forge start``.

Replaces the stub from Story 1.1 with the full pipeline:
prompt -> render -> install -> success.
"""

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


def start_project(
    *, project_name: str, no_input: bool = False
) -> None:
    """Scaffold a new Django project.

    Full end-to-end flow:
    1. Detect CI/no-input mode
    2. Brand banner
    3. Check target directory
    4. Confirm scaffold settings with user
    5. Generate template files via renderer
    6. Install dependencies, migrate, deploy-check
    7. Print success banner with next steps
    """
    # 0. Detect CI / no-input mode
    ci_detected = False
    if not no_input and _is_ci_env():
        ci_detected = True
        no_input = True

    # 1. Brand banner
    _print_banner(project_name, no_input=no_input, ci_detected=ci_detected)

    # 2. Check target directory
    target_dir = Path.cwd() / project_name
    if no_input and target_dir.exists():
        import shutil
        shutil.rmtree(target_dir)
    elif target_dir.exists() and not _handle_existing_directory(target_dir):
        return

    # 3. Confirm scaffold settings
    secret_key = _generate_secret_key()
    context = confirm_scaffold(
        project_name, api=None, db=None, layers=None, no_input=no_input,
    )
    if context is None:
        return
    context["secret_key"] = secret_key

    save_prefs(api=context["api"], db=context["db"], layers=context["layers"])

    # 4. Generate template files
    renderer = _get_renderer()
    console.print()
    console.print(
        f"  [forge.label]Forging [forge.highlight]{project_name}[/]..."
    )
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
        f"  [forge.label]Forge your Django project:[/]  "
        f"[forge.highlight]{project_name}[/]"
    )
    if no_input:
        console.print()
        if ci_detected:
            console.print(
                "  [forge.info]CI mode detected"
                " - using defaults[/]"
            )
        else:
            console.print(
                "  [forge.info]Using defaults"
                " (--no-input mode)[/]"
            )


def _handle_existing_directory(target_dir: Path) -> bool:
    """Prompt user about overwriting an existing directory.

    Returns ``True`` if the caller should continue (directory cleared),
    ``False`` if the user chose to abort.
    """
    import shutil

    console.print()
    console.print(
        "  [forge.warning]"
        f"Directory [forge.highlight]{target_dir.name}[/]"
        " already exists"
        "[/]"
    )
    console.print()

    response = input("  Overwrite? [y/N] ").strip().lower()
    if response not in ("y", "yes"):
        console.print(
            "  [forge.muted]Aborted. No files were changed.[/]"
        )
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
    template_root = (
        Path(__file__).resolve().parent.parent / "templates"
    )
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
    console.print(
        "    [forge.highlight]uv run manage.py runserver[/]"
    )
    console.print()
    console.print(
        "  [forge.label]Set production environment variables:[/]"
    )
    console.print(
        "    [forge.highlight]cp .env.example .env[/]"
    )
    console.print(
        "    [forge.muted](edit .env with your secrets)[/]"
    )
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
        console.print(
            "  [forge.muted]"
            "Non-interactive environment — skipping createsuperuser."
            "[/]"
        )
        console.print()
        return

    console.print()
    response = input("  Create a superuser account? [y/N] ").strip().lower()
    if response not in ("y", "yes"):
        console.print("  [forge.muted]Skipped. You can create one later with:[/]")
        console.print(
            f"    [forge.highlight]cd {project_dir.name}"
            " && uv run manage.py createsuperuser[/]"
        )
        console.print()
        return

    console.print()
    console.print(
        "  [forge.label]Running [forge.highlight]"
        "createsuperuser[/]..."
    )
    console.print()
    try:
        subprocess.run(
            ["uv", "run", "manage.py", "createsuperuser"],
            cwd=str(project_dir),
            check=False,
        )
    except FileNotFoundError:
        console.print(
            "  [forge.error]uv not found — cannot run createsuperuser.[/]"
        )
    console.print()
