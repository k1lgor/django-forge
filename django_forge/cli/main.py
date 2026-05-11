"""Entry point for the forge CLI application."""

import typer

from django_forge import __version__

app = typer.Typer(
    name="forge",
    help="django-forge - Scaffold production-ready Django projects.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["--help", "-h"]},
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"forge v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """django-forge — Scaffold production-ready Django projects."""
    pass


@app.command()
def start(
    project_name: str = typer.Argument(..., help="Name of the project directory to create"),
    no_input: bool = typer.Option(
        False,
        "--no-input",
        help="Skip interactive prompts and use sensible defaults.",
    ),
) -> None:
    """Create a new Django project with best-practice defaults."""
    from django_forge.cli.start import start_project

    start_project(project_name=project_name, no_input=no_input)


@app.command()
def list() -> None:
    """Show available frameworks and optional layers."""
    from django_forge.cli.list_cmd import list_options

    list_options()


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
