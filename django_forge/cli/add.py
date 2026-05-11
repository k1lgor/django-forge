"""``forge add <layer>`` — add optional layers to existing forge projects."""

from pathlib import Path

from rich.prompt import Confirm

from django_forge.cli.console import console
from django_forge.renderer import Renderer

_VALID_LAYERS = {"docker", "celery", "email"}


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
            " Available: docker, celery, email."
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
        console.print(
            f"  [forge.info]{layer.capitalize()} already installed.[/]"
        )
        return

    # Build updated context
    context = _build_add_context(project_context, layer)

    # Dispatch to layer handler
    renderer = _get_renderer()

    success = False
    if layer == "docker":
        success = _add_docker(project_dir, context, renderer, existing_layers)
    elif layer == "celery":
        success = _add_celery(project_dir, context, renderer, existing_layers)
    elif layer == "email":
        success = _add_email(project_dir, context, renderer, existing_layers)

    if not success:
        console.print(
            "  [forge.muted]No files were changed.[/]"
        )
        return

    # Update .forge.toml
    new_layers = [*list(existing_layers), layer]
    _update_forge_toml(project_dir / ".forge.toml", new_layers)

    console.print()
    console.print(
        f"  [forge.success]Added [forge.highlight]{layer}[/] layer.[/]"
    )
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
        console.print(
            "  [forge.error]Not a forge project.[/]"
        )
        console.print(
            "  [forge.muted]"
            "Run [forge.highlight]forge start myproject[/]"
            " first."
            "[/]"
        )
        return None

    try:
        import tomli

        raw = forge_toml.read_text(encoding="utf-8")
        data = tomli.loads(raw)
        forge_section = data.get("forge", {})
        if not forge_section:
            console.print()
            console.print(
                "  [forge.error]Not a forge project.[/]"
            )
            return None
        return {
            "api": forge_section.get("api", "drf"),
            "db": forge_section.get("db", "postgres"),
            "layers": forge_section.get("layers", []),
        }
    except Exception:
        console.print()
        console.print(
            "  [forge.error]"
            "Invalid .forge.toml. The file may be corrupted."
            "[/]"
        )
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
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _get_renderer() -> Renderer:
    """Get a Renderer pointing to the embedded template tree."""
    template_root = (
        Path(__file__).resolve().parent.parent / "templates"
    )
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
    console.print(
        "  [forge.label]Adding [forge.highlight]Docker[/] layer...[/]"
    )

    modified: list[tuple[Path, str]] = [
        (project_dir / "Dockerfile", "Dockerfile"),
        (project_dir / "compose.yaml", "compose.yaml"),
        (project_dir / ".dockerignore", ".dockerignore"),
    ]
    if not _confirm_existing_files(modified):
        return False

    renderer.render_project(context, project_dir)
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
    console.print(
        "  [forge.label]Adding [forge.highlight]Celery[/] layer...[/]"
    )

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

    renderer.render_project(context, project_dir)
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
    console.print(
        "  [forge.label]Adding [forge.highlight]Email[/] layer...[/]"
    )

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

    renderer.render_project(context, project_dir)
    return True


# ---------------------------------------------------------------------------
# .forge.toml update
# ---------------------------------------------------------------------------


def _update_forge_toml(path: Path, layers: list[str]) -> None:
    """Update the layers list in an existing .forge.toml."""
    import tomli

    raw = path.read_text(encoding="utf-8")
    data = tomli.loads(raw)
    if "forge" not in data:
        data["forge"] = {}
    data["forge"]["layers"] = sorted(set(layers))

    # Manual TOML serialization — avoids adding tomli_w dependency
    api = data["forge"].get("api", "drf")
    db = data["forge"].get("db", "postgres")
    version = data["forge"].get("version", "0.1.0")
    items = ", ".join(f'"{layer}"' for layer in sorted(set(layers)))
    toml_content = (
        f'[forge]\n'
        f'version = "{version}"\n'
        f'api = "{api}"\n'
        f'db = "{db}"\n'
        f'layers = [{items}]\n'
    )
    path.write_text(toml_content, encoding="utf-8")


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
    console.print(
        "  [forge.warning]"
        "The following files will be overwritten:"
        "[/]"
    )
    for _path, label in existing:
        console.print(f"    [forge.muted]- {label}[/]")
    console.print()
    return Confirm.ask(
        "  [forge.prompt]Overwrite these files?[/]",
        default=False,
    )
