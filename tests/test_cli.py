"""Tests for the forge CLI entry point."""

from typer.testing import CliRunner

from django_forge import __version__
from django_forge.cli.main import app

runner = CliRunner()


def test_version() -> None:
    """Running `forge --version` prints the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"forge v{__version__}" in result.stdout


def test_help_shows_commands() -> None:
    """Running `forge --help` lists all commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "start" in result.stdout
    assert "list" in result.stdout
    assert "add" in result.stdout
    assert "django-forge" in result.stdout


def test_start_help_shows_usage() -> None:
    """Running `forge start --help` shows PROJECT_NAME and --no-input."""
    result = runner.invoke(app, ["start", "--help"])
    assert result.exit_code == 0
    assert "PROJECT_NAME" in result.stdout
    assert "--no-input" in result.stdout


def test_start_command_accepts_project_name() -> None:
    """Running `forge start myproject` shows the project name in output."""
    result = runner.invoke(app, ["start", "myproject"], input="n\n")
    # Should exit cleanly (0) or with graceful abort
    assert "myproject" in result.stdout


def test_list_shows_available_options() -> None:
    """Running `forge list` shows available frameworks and layers."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Available Frameworks" in result.stdout
    assert "DRF" in result.stdout
    assert "Django-Ninja" in result.stdout
    assert "Pure Django" in result.stdout
    assert "Available Optional Layers" in result.stdout
    assert "Docker" in result.stdout
    assert "Celery" in result.stdout
    assert "Email" in result.stdout
    assert "Core Layers" in result.stdout


def test_add_rejects_non_forge_project() -> None:
    """Running `forge add celery` outside a forge project shows error."""
    result = runner.invoke(app, ["add", "celery"])
    assert result.exit_code == 0
    assert "Not a forge project" in result.stdout


def test_add_unknown_layer() -> None:
    """Running `forge add foo` shows unknown layer error."""
    result = runner.invoke(app, ["add", "foo"])
    assert result.exit_code == 0
    assert "Unknown layer" in result.stdout


def test_import_version() -> None:
    """The package is importable and exposes __version__."""
    from django_forge import __version__ as ver

    assert ver == "0.2.0"


def test_h_alias_shows_help() -> None:
    """Running `forge -h` shows help (same as --help)."""
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0, (
        f"Expected -h to show help but got exit code {result.exit_code}. "
        f"This is a defect — -h should be an alias for --help.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "start" in result.stdout
    assert "list" in result.stdout
    assert "add" in result.stdout


def test_no_args_shows_help() -> None:
    """Running `forge` with no args shows help (no_args_is_help=True)."""
    result = runner.invoke(app)
    assert result.exit_code in (0, 2), f"Expected exit code 0 or 2, got {result.exit_code}"
    assert "Usage:" in result.stdout
