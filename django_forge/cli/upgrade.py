"""``forge upgrade`` — re-apply all templates to an existing project."""

from pathlib import Path

from django_forge import __version__ as _forge_version
from django_forge.cli.add import (
    _confirm_existing_files,
    _load_existing_secret,
    _update_forge_toml,
)
from django_forge.cli.console import console
from django_forge.cli.start import _get_renderer


def upgrade_project() -> None:
    """Re-render all templates into the current project directory.

    Reads ``.forge.toml``, builds the full context from existing settings,
    re-renders every template, and updates ``.forge.toml`` with the latest
    version number.
    """
    project_dir = Path.cwd()

    # Detect project context
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

    # Build full context from existing settings
    existing_layers: list[str] = project_context.get("layers", [])
    api = project_context.get("api", "drf")
    db = project_context.get("db", "postgres")
    project_name = project_dir.name
    project_slug = project_name.replace("-", "_").replace(" ", "_")
    secret_key = _load_existing_secret(project_dir)

    context = {
        "project_name": project_name,
        "project_slug": project_slug,
        "secret_key": secret_key,
        "api": api,
        "db": db,
        "layers": list(existing_layers),
        "use_drf": api == "drf",
        "use_ninja": api == "ninja",
        "use_pure_django": api == "pure",
        "has_docker": "docker" in existing_layers,
        "has_celery": "celery" in existing_layers,
        "has_email": "email" in existing_layers,
        "has_cache": "cache" in existing_layers,
        "has_social": "social" in existing_layers,
        "has_storage": "storage" in existing_layers,
        "has_healthcheck": "healthcheck" in existing_layers,
        "has_audit": "audit" in existing_layers,
        "has_backup": "backup" in existing_layers,
        "has_seed": "seed" in existing_layers,
        "has_preflight": "preflight" in existing_layers,
        "forge_version": _forge_version,
    }

    # Collect files that will be overwritten
    renderer = _get_renderer()
    template_root = renderer.template_root

    existing_files: list[tuple[Path, str]] = []
    for template_path in sorted(template_root.rglob("*")):
        if not template_path.is_file():
            continue
        if template_path.suffix == ".j2":
            rel = template_path.relative_to(template_root)
            output_name = rel.parent / rel.stem
        else:
            output_name = template_path.relative_to(template_root)
        output_path = project_dir / output_name
        if output_path.exists() and output_name.name != ".forge.toml":
            existing_files.append((output_path, str(output_name)))

    if not existing_files:
        console.print()
        console.print("  [forge.muted]No existing project files found to upgrade.[/]")
        return

    console.print()
    console.print(
        f"  [forge.label]Checking templates for [forge.highlight]{project_dir.name}[/]...[/]"
    )

    if not _confirm_existing_files(existing_files):
        console.print("  [forge.muted]Upgrade cancelled. No files were changed.[/]")
        return

    console.print()
    console.print("  [forge.label]Upgrading project templates...[/]")
    renderer.render_project(context, project_dir, policy="pristine")
    for output_name, _reason in renderer.skipped:
        console.print(f"  [forge.muted]Skipped {output_name} (user-modified)[/]")

    # Update .forge.toml version
    _update_forge_toml(project_dir / ".forge.toml", list(existing_layers))

    console.print()
    console.print("  [forge.success]Project upgraded to latest templates.[/]")
    console.print()


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
