"""Entry point for the forge-django CLI application."""

from typing import Literal

import typer

from django_forge import __version__

app = typer.Typer(
    name="forge-django",
    help="django-forge - Scaffold production-ready Django projects.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["--help", "-h"]},
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"forge-django v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(  # noqa: ARG001 - consumed by the eager callback
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Mirror subprocess output live and print extra diagnostics.",
    ),
) -> None:
    """django-forge — Scaffold production-ready Django projects."""
    from django_forge.cli.installer import set_verbose

    set_verbose(verbose)


@app.command()
def start(
    project_name: str = typer.Argument(..., help="Name of the project directory to create"),
    no_input: bool = typer.Option(
        False,
        "--no-input",
        help="Skip interactive prompts and use sensible defaults.",
    ),
    api: Literal["drf", "ninja", "pure"] | None = typer.Option(
        None,
        "--api",
        help="API framework; overrides the --no-input default (drf).",
    ),
    db: Literal["postgres", "sqlite"] | None = typer.Option(
        None,
        "--db",
        help="Database setup; overrides the --no-input default (postgres).",
    ),
    layers: str | None = typer.Option(
        None,
        "--layers",
        help=(
            "Comma-separated optional layer slugs (e.g. docker,celery); "
            "overrides the --no-input default (no layers)."
        ),
    ),
) -> None:
    """Create a new Django project with best-practice defaults."""
    from django_forge.cli.start import start_project

    layer_slugs = (
        None if layers is None else [slug.strip() for slug in layers.split(",") if slug.strip()]
    )
    start_project(
        project_name=project_name,
        no_input=no_input,
        api=api,
        db=db,
        layers=layer_slugs,
    )


@app.command("list")
def list_options() -> None:
    """Show available frameworks and optional layers."""
    from django_forge.cli.list_cmd import list_options as render_options

    render_options()


@app.command()
def add(
    layer: str = typer.Argument(..., help="Layer to add (e.g., celery, docker, email)"),
) -> None:
    """Add an optional layer to an existing project."""
    from django_forge.cli.add import add_layer

    add_layer(layer=layer)


@app.command()
def upgrade() -> None:
    """Re-apply all templates to an existing project."""
    from django_forge.cli.upgrade import upgrade_project

    upgrade_project()
