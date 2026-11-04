"""``forge-django add <layer>`` — add optional layers to existing forge projects."""

import importlib
import re
from pathlib import Path

import typer
from rich.prompt import Confirm

from django_forge.cli.console import console
from django_forge.cli.start import _generate_secret_key
from django_forge.project import LAYER_IDS as _VALID_LAYER_IDS
from django_forge.project import build_context, detect_project, update_layers
from django_forge.registry import LAYERS
from django_forge.renderer import Renderer

_SECRET_RE_ENV = re.compile(r'^DJANGO_SECRET_KEY\s*=\s*"?([^"\n#]+)', re.MULTILINE)
_SECRET_RE_SETTINGS = re.compile(r'django_secret_key:\s*str\s*=\s*"([^"]+)"')


def add_layer(*, layer: str) -> None:
    """Add an optional layer to an existing forge-generated project.

    Args:
        layer: Name of the layer to add (docker, celery, email, ...).

    Raises:
        typer.Exit: With code 1 on every failure path (unknown layer, not a
            forge project, already installed, refused overwrite, failed
            render or manifest update).
    """
    layer = layer.strip().lower()

    if layer not in _VALID_LAYER_IDS:
        console.print(
            f"  [forge.error]Unknown layer: '{layer}'. Available: {', '.join(_VALID_LAYER_IDS)}.[/]"
        )
        raise typer.Exit(code=1)

    # Detect project context from .forge.toml in CWD (shared module).
    project_dir = Path.cwd()
    state = detect_project(project_dir)
    if state is None:
        raise typer.Exit(code=1)

    existing_layers: list[str] = state.get("layers", [])
    if layer in existing_layers:
        console.print()
        console.print(f"  [forge.info]{layer.capitalize()} already installed.[/]")
        raise typer.Exit(code=1)

    # Build the render context with the NEW layer already recorded — layer-gated
    # templates must render non-empty for it, otherwise the renderer skips them
    # and the command would claim success while writing nothing (entry 28).
    state = {**state, "layers": [*existing_layers, layer]}
    context = build_context(state)
    context["secret_key"] = _load_existing_secret(project_dir) or _generate_secret_key()

    # Confirm every file a pristine render would actually rewrite — computed
    # from on-disk bytes (design entry 28), not from a hand-maintained list.
    renderer = _get_renderer()
    candidates = renderer.preview_overwrites(context, project_dir)
    if candidates and not _confirm_existing_files(candidates):
        console.print("  [forge.muted]Add cancelled. No files were changed.[/]")
        raise typer.Exit(code=1)

    # Dispatch to the layer handler.
    success = _dispatch_layer(layer, project_dir, context, renderer)
    if not success:
        console.print("  [forge.muted]No files were changed.[/]")
        raise typer.Exit(code=1)

    # Update .forge.toml (textual — comments/extra sections survive).
    update_layers(project_dir / ".forge.toml", [*existing_layers, layer])

    console.print()
    console.print(f"  [forge.success]Added [forge.highlight]{layer}[/] layer.[/]")
    console.print()


def _dispatch_layer(layer: str, project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Route the layer to its handler through the registry's dotted string."""
    entry = next((item for item in LAYERS if item.id == layer), None)
    if entry is None:  # pragma: no cover - guarded by _VALID_LAYER_IDS
        return False
    module_name, _, func_name = entry.handler.partition(":")
    handler = getattr(importlib.import_module(module_name), func_name)
    return handler(project_dir, context, renderer)


# ---------------------------------------------------------------------------
# Secret recovery
# ---------------------------------------------------------------------------


def _load_existing_secret(project_dir: Path) -> str:
    """Return the project's existing SECRET_KEY, or ``""`` if none found.

    Reads ``DJANGO_SECRET_KEY`` from ``.env`` first, then (pre-0.4 projects)
    the ``django_secret_key`` default from ``config/settings/base.py``. This
    keeps re-renders (``forge-django add`` / ``upgrade``) from blanking the
    secret, which the render context does not carry.
    """
    env_file = project_dir / ".env"
    if env_file.exists():
        match = _SECRET_RE_ENV.search(env_file.read_text(encoding="utf-8"))
        if match:
            return match.group(1).strip()
    base_py = project_dir / "config" / "settings" / "base.py"
    if base_py.exists():
        match = _SECRET_RE_SETTINGS.search(base_py.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return ""


def _get_renderer() -> Renderer:
    """Get a Renderer pointing to the embedded template tree."""
    template_root = Path(__file__).resolve().parent.parent / "templates"
    return Renderer(template_root)


# ---------------------------------------------------------------------------
# Layer handlers
# ---------------------------------------------------------------------------


def _add_docker(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Docker layer to an existing project (Dockerfile, compose, ignore)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Docker[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_celery(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Celery layer to an existing project."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Celery[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_email(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Email layer to an existing project (settings + .env.example)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Email[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_cache(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Caching layer to an existing project."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Caching[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_social(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Social Auth layer to an existing project.

    Note: ``urls.py`` is not re-rendered for this layer's sake — social auth
    URLs are already served by the ``path("accounts/", include("allauth.urls"))``
    route; the shared render still refreshes every other owned file.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Social Auth[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_storage(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add S3 Storage layer to an existing project."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]S3 Storage[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_healthcheck(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Health Check layer (mounts django-health-check at ``/healthz/``)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Health Check[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    console.print()
    console.print("  [forge.label]Next steps (new dependency + health-check tables):[/]")
    console.print("    [forge.highlight]uv sync[/]")
    console.print("    [forge.highlight]uv run manage.py migrate[/]")
    return True


def _add_audit(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Audit Trail layer (django-simple-history on the User model)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Audit Trail[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    console.print()
    console.print("  [forge.label]Next steps (new dependency + schema change):[/]")
    console.print("    [forge.highlight]uv sync[/]")
    console.print("    [forge.highlight]uv run manage.py makemigrations accounts[/]")
    console.print("    [forge.highlight]uv run manage.py migrate[/]")
    return True


def _add_backup(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Backup layer (django-dbbackup dumps + ``make backup``/``restore``)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Backup[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_seed(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Seed Data layer (factory-boy data + ``manage.py seed``)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Seed Data[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


def _add_preflight(project_dir: Path, context: dict, renderer: Renderer) -> bool:
    """Add Preflight layer (``manage.py preflight`` pre-deploy checks)."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Preflight[/] layer...[/]")
    _render_layers(renderer, context, project_dir)
    return True


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_layers(renderer: Renderer, context: dict, project_dir: Path) -> None:
    """Re-render the project tree, leaving user-edited files untouched.

    Uses ``policy="pristine"``: files forge wrote and the user has not
    modified are refreshed; user-modified or user-created files are skipped
    and reported.
    """
    renderer.render_project(context, project_dir, policy="pristine")
    for output_name, _reason in renderer.skipped:
        console.print(f"  [forge.muted]Skipped {output_name} (user-modified)[/]")


# ---------------------------------------------------------------------------
# Overwrite confirmation
# ---------------------------------------------------------------------------


def _confirm_existing_files(files: list[tuple[Path, str]]) -> bool:
    """Ask the user before overwriting *files* (list of ``(path, label)``).

    Returns ``True`` to proceed, ``False`` when the user refuses.
    """
    if not files:
        return True
    console.print()
    console.print("  [forge.warning]The following files will be overwritten:[/]")
    for _path, label in files:
        console.print(f"    [forge.muted]- {label}[/]")
    console.print()
    return Confirm.ask(
        "  [forge.prompt]Overwrite these files?[/]",
        default=False,
    )
