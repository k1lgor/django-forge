"""``forge-django upgrade`` — re-apply all templates to an existing project."""

from pathlib import Path

import typer
from rich.prompt import Confirm

from django_forge.cli.add import _confirm_existing_files, _load_existing_secret
from django_forge.cli.console import console
from django_forge.cli.start import _generate_secret_key, _get_renderer
from django_forge.project import build_context, detect_project, update_layers
from django_forge.renderer import MANIFEST_NAME


def upgrade_project() -> None:
    """Re-render all templates into the current project directory.

    Reads ``.forge.toml`` (including the project identity written there),
    builds the full context through the shared builder, confirms the files
    that would actually change, re-renders every template, and rewrites
    ``layers`` + ``version`` in ``.forge.toml`` textually.

    Raises:
        typer.Exit: With code 1 when this is not a forge project, the
            manifest baseline is missing and the user refuses, the overwrite
            is refused, or the render/update fails.
    """
    project_dir = Path.cwd()

    state = detect_project(project_dir)
    if state is None:
        raise typer.Exit(code=1)

    existing_layers: list[str] = state.get("layers", [])
    context = build_context(state)
    # Empty recovery means no persisted secret: mint a fresh key instead of
    # rendering a blank one (mirrors add.py's fallback).
    context["secret_key"] = _load_existing_secret(project_dir) or _generate_secret_key()

    # Missing manifest = unknown baseline: refuse and ask before overwriting
    # (M8; policy documented on the Renderer class).
    if not (project_dir / MANIFEST_NAME).exists():
        console.print()
        console.print(
            "  [forge.warning]No .forge-manifest.json — forge cannot tell its"
            " files from yours (unknown baseline).[/]"
        )
        if not Confirm.ask(
            "  [forge.prompt]Upgrade anyway and overwrite differing files?[/]",
            default=False,
        ):
            console.print("  [forge.muted]Upgrade cancelled. No files were changed.[/]")
            raise typer.Exit(code=1)

    renderer = _get_renderer()
    candidates = renderer.preview_overwrites(context, project_dir)

    console.print()
    console.print(
        f"  [forge.label]Checking templates for [forge.highlight]{project_dir.name}[/]...[/]"
    )
    if candidates and not _confirm_existing_files(candidates):
        console.print("  [forge.muted]Upgrade cancelled. No files were changed.[/]")
        raise typer.Exit(code=1)

    console.print()
    console.print("  [forge.label]Upgrading project templates...[/]")
    renderer.render_project(context, project_dir, policy="pristine")
    for output_name, _reason in renderer.skipped:
        console.print(f"  [forge.muted]Skipped {output_name} (user-modified)[/]")

    # Textual update: layers unchanged, version bumped to this release.
    update_layers(project_dir / ".forge.toml", list(existing_layers))

    console.print()
    console.print("  [forge.success]Project upgraded to latest templates.[/]")
    console.print()
