"""``forge add <layer>`` — add optional layers to existing forge projects."""

import re
from pathlib import Path

from rich.prompt import Confirm

from django_forge import __version__ as _forge_version
from django_forge.cli.console import console
from django_forge.cli.start import _generate_secret_key
from django_forge.renderer import Renderer

_VALID_LAYERS = {
    "docker",
    "celery",
    "email",
    "cache",
    "social",
    "storage",
    "healthcheck",
    "audit",
    "backup",
    "seed",
    "preflight",
}

_SECRET_RE_ENV = re.compile(r'^DJANGO_SECRET_KEY\s*=\s*"?([^"\n#]+)', re.MULTILINE)
_SECRET_RE_SETTINGS = re.compile(r'django_secret_key:\s*str\s*=\s*"([^"]+)"')


def add_layer(*, layer: str) -> None:
    """Add an optional layer to an existing forge-generated project.

    Args:
        layer: Name of the layer to add (docker, celery, email).
    """
    layer = layer.strip().lower()

    # Validate layer name
    if layer not in _VALID_LAYERS:
        console.print(
            "  [forge.error]"
            f"Unknown layer: '{layer}'."
            " Available: docker, celery, email, cache, social, storage,"
            " healthcheck, audit, backup, seed, preflight."
            "[/]"
        )
        return

    # Detect project context from .forge.toml in CWD
    project_dir = Path.cwd()
    project_context = _detect_project(project_dir)
    if project_context is None:
        console.print()
        console.print(
            "  [forge.success]"
            "Run [forge.highlight]forge start myproject[/]"
            " first to create a project."
            "[/]"
        )
        return

    # Check if layer is already installed
    existing_layers: list[str] = project_context.get("layers", [])
    if layer in existing_layers:
        console.print()
        console.print(f"  [forge.info]{layer.capitalize()} already installed.[/]")
        return

    # Build updated context
    context = _build_add_context(project_context, layer)
    context["secret_key"] = _load_existing_secret(project_dir) or _generate_secret_key()

    # Dispatch to layer handler
    renderer = _get_renderer()

    success = False
    if layer == "docker":
        success = _add_docker(project_dir, context, renderer, existing_layers)
    elif layer == "celery":
        success = _add_celery(project_dir, context, renderer, existing_layers)
    elif layer == "email":
        success = _add_email(project_dir, context, renderer, existing_layers)
    elif layer == "cache":
        success = _add_cache(project_dir, context, renderer, existing_layers)
    elif layer == "social":
        success = _add_social(project_dir, context, renderer, existing_layers)
    elif layer == "storage":
        success = _add_storage(project_dir, context, renderer, existing_layers)
    elif layer == "healthcheck":
        success = _add_healthcheck(project_dir, context, renderer, existing_layers)
    elif layer == "audit":
        success = _add_audit(project_dir, context, renderer, existing_layers)
    elif layer == "backup":
        success = _add_backup(project_dir, context, renderer, existing_layers)
    elif layer == "seed":
        success = _add_seed(project_dir, context, renderer, existing_layers)
    elif layer == "preflight":
        success = _add_preflight(project_dir, context, renderer, existing_layers)

    if not success:
        console.print("  [forge.muted]No files were changed.[/]")
        return

    # Update .forge.toml
    new_layers = [*list(existing_layers), layer]
    _update_forge_toml(project_dir / ".forge.toml", new_layers)

    console.print()
    console.print(f"  [forge.success]Added [forge.highlight]{layer}[/] layer.[/]")
    console.print()


# ---------------------------------------------------------------------------
# Project detection
# ---------------------------------------------------------------------------


def _detect_project(project_dir: Path) -> dict | None:
    """Read .forge.toml and return the project context dict.

    Returns ``None`` if the file is missing or invalid.
    """
    forge_toml = project_dir / ".forge.toml"
    if not forge_toml.exists():
        console.print()
        console.print("  [forge.error]Not a forge project.[/]")
        console.print("  [forge.muted]Run [forge.highlight]forge start myproject[/] first.[/]")
        return None

    try:
        import tomli

        raw = forge_toml.read_text(encoding="utf-8")
        data = tomli.loads(raw)
        forge_section = data.get("forge", {})
        if not forge_section:
            console.print()
            console.print("  [forge.error]Not a forge project.[/]")
            return None
        return {
            "api": forge_section.get("api", "drf"),
            "db": forge_section.get("db", "postgres"),
            "layers": forge_section.get("layers", []),
        }
    except Exception:
        console.print()
        console.print("  [forge.error]Invalid .forge.toml. The file may be corrupted.[/]")
        return None


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


def _build_add_context(project_context: dict, new_layer: str) -> dict:
    """Build the full render context for an add operation."""
    api = project_context.get("api", "drf")
    db = project_context.get("db", "postgres")
    existing_layers: list[str] = project_context.get("layers", [])
    all_layers = [*list(existing_layers), new_layer]

    # Determine project name from CWD
    project_name = Path.cwd().name
    project_slug = project_name.replace("-", "_").replace(" ", "_")

    return {
        "project_name": project_name,
        "project_slug": project_slug,
        "secret_key": "",
        "api": api,
        "db": db,
        "layers": all_layers,
        "use_drf": api == "drf",
        "use_ninja": api == "ninja",
        "use_pure_django": api == "pure",
        "has_docker": "docker" in all_layers,
        "has_celery": "celery" in all_layers,
        "has_email": "email" in all_layers,
        "has_cache": "cache" in all_layers,
        "has_social": "social" in all_layers,
        "has_storage": "storage" in all_layers,
        "has_healthcheck": "healthcheck" in all_layers,
        "has_audit": "audit" in all_layers,
        "has_backup": "backup" in all_layers,
        "has_seed": "seed" in all_layers,
        "has_preflight": "preflight" in all_layers,
        "forge_version": _forge_version,
    }


# ---------------------------------------------------------------------------
# Renderer
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


def _load_existing_secret(project_dir: Path) -> str:
    """Return the project's existing SECRET_KEY, or ``""`` if none found.

    Reads ``DJANGO_SECRET_KEY`` from ``.env`` first, then the
    ``django_secret_key`` default from ``config/settings/base.py``. This
    keeps re-renders (``forge add`` / ``forge upgrade``) from blanking
    the secret, which the render context does not carry.
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


def _add_docker(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Docker layer to an existing project.

    Returns ``True`` if the operation succeeded, ``False`` if skipped.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Docker[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "Dockerfile", "Dockerfile"),
        (project_dir / "compose.yaml", "compose.yaml"),
        (project_dir / ".dockerignore", ".dockerignore"),
    ]
    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_celery(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    existing_layers: list[str],
) -> bool:
    """Add Celery layer to an existing project.

    Returns ``True`` if the operation succeeded, ``False`` if skipped.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Celery[/] layer...[/]")

    # Files that will be re-rendered (overwritten)
    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "config" / "__init__.py", "config/__init__.py"),
        (project_dir / "pyproject.toml", "pyproject.toml"),
    ]
    if "docker" in existing_layers:
        modified.append((project_dir / "compose.yaml", "compose.yaml"))

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_email(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    existing_layers: list[str],
) -> bool:
    """Add Email layer to an existing project.

    Returns ``True`` if the operation succeeded, ``False`` if skipped.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Email[/] layer...[/]")

    # Files that will be re-rendered (overwritten)
    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "config" / "settings" / "dev.py", "dev.py"),
        (project_dir / "config" / "settings" / "prod.py", "prod.py"),
        (project_dir / ".env.example", ".env.example"),
    ]
    if "docker" in existing_layers:
        modified.append((project_dir / "compose.yaml", "compose.yaml"))

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_cache(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    existing_layers: list[str],
) -> bool:
    """Add Caching layer to an existing project.

    Returns ``True`` if the operation succeeded, ``False`` if skipped.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Caching[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "pyproject.toml", "pyproject.toml"),
    ]
    if "docker" in existing_layers and "celery" not in existing_layers:
        modified.append((project_dir / "compose.yaml", "compose.yaml"))

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_social(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Social Auth layer to an existing project.

    Note: ``urls.py`` is not re-rendered because social auth URLs
    are already handled by the existing ``path('accounts/', include('allauth.urls'))``
    route — no additional URL patterns are needed.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Social Auth[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / ".env.example", ".env.example"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_storage(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add S3 Storage layer to an existing project."""
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]S3 Storage[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "config" / "settings" / "prod.py", "prod.py"),
        (project_dir / "pyproject.toml", "pyproject.toml"),
        (project_dir / ".env.example", ".env.example"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_healthcheck(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Health Check layer to an existing project.

    Mounts django-health-check at ``/healthz/`` with DB (always) and
    cache/celery checks when those layers are present.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Health Check[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "config" / "urls.py", "config/urls.py"),
        (project_dir / "pyproject.toml", "pyproject.toml"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)

    console.print()
    console.print("  [forge.label]Next steps (new dependency + health-check tables):[/]")
    console.print("    [forge.highlight]uv sync[/]")
    console.print("    [forge.highlight]uv run manage.py migrate[/]")
    return True


def _add_audit(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Audit Trail layer to an existing project.

    Records every change to the custom User model via django-simple-history.
    Schema-changing: after rendering, run ``uv sync``, then
    ``makemigrations accounts`` and ``migrate`` (printed as next steps).
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Audit Trail[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "apps" / "accounts" / "models.py", "models.py"),
        (project_dir / "apps" / "accounts" / "admin.py", "admin.py"),
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "pyproject.toml", "pyproject.toml"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)

    console.print()
    console.print("  [forge.label]Next steps (new dependency + schema change):[/]")
    console.print("    [forge.highlight]uv sync[/]")
    console.print("    [forge.highlight]uv run manage.py makemigrations accounts[/]")
    console.print("    [forge.highlight]uv run manage.py migrate[/]")
    return True


def _add_backup(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Backup layer to an existing project.

    django-dbbackup dumps the database (to S3 when the storage layer is
    present, else to ``backups/``) with ``make backup`` / ``make restore``.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Backup[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "config" / "settings" / "base.py", "base.py"),
        (project_dir / "pyproject.toml", "pyproject.toml"),
        (project_dir / "Makefile", "Makefile"),
        (project_dir / "README.md", "README.md"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_seed(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Seed Data layer to an existing project.

    Ships a factory-based ``UserFactory`` and a ``manage.py seed`` command
    that creates sample users in dev.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Seed Data[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "Makefile", "Makefile"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


def _add_preflight(
    project_dir: Path,
    context: dict,
    renderer: Renderer,
    _existing_layers: list[str],
) -> bool:
    """Add Preflight layer to an existing project.

    Ships ``manage.py preflight`` — one command that runs the deploy check,
    a pending-migrations check, and ``migrate --check`` before you push.
    """
    console.print()
    console.print("  [forge.label]Adding [forge.highlight]Preflight[/] layer...[/]")

    modified: list[tuple[Path, str]] = [
        (project_dir / "Makefile", "Makefile"),
    ]

    if not _confirm_existing_files(modified):
        return False

    _render_layers(renderer, context, project_dir)
    return True


# ---------------------------------------------------------------------------
# .forge.toml update
# ---------------------------------------------------------------------------


def _update_forge_toml(path: Path, layers: list[str]) -> None:
    """Update the layers list in an existing .forge.toml.

    Preserves every other key in ``[forge]`` and any additional top-level
    sections (e.g. ``[database]``). Plain string/list/scalar values are
    serialized manually to avoid adding a tomli_w dependency.
    """
    import tomli

    raw = path.read_text(encoding="utf-8")
    data = tomli.loads(raw)
    data.setdefault("forge", {})
    data["forge"]["layers"] = sorted(set(layers))

    lines: list[str] = ["[forge]"]
    forge = data.pop("forge")
    lines.extend(_serialize_table(forge))
    for section in sorted(data):
        lines.append("")
        lines.append(f"[{section}]")
        lines.extend(_serialize_table(data[section]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _serialize_table(table: dict) -> list[str]:
    """Serialize a flat TOML table (strings, lists, scalars) as lines."""
    lines: list[str] = []
    for key, value in table.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key} = {value}")
        elif isinstance(value, list):
            items = ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in value)
            lines.append(f"{key} = [{items}]")
        else:
            lines.append(f'{key} = "{value}"')
    return lines


# ---------------------------------------------------------------------------
# Overwrite confirmation
# ---------------------------------------------------------------------------


def _confirm_existing_files(files: list[tuple[Path, str]]) -> bool:
    """Check for existing files and prompt user before overwriting.

    Args:
        files: List of ``(path, label)`` tuples to check.

    Returns:
        ``True`` if the user agrees to overwrite, ``False`` to skip.
    """
    existing = [(path, label) for path, label in files if path.exists()]
    if not existing:
        return True

    console.print()
    console.print("  [forge.warning]The following files will be overwritten:[/]")
    for _path, label in existing:
        console.print(f"    [forge.muted]- {label}[/]")
    console.print()
    return Confirm.ask(
        "  [forge.prompt]Overwrite these files?[/]",
        default=False,
    )
