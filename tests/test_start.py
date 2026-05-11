"""End-to-end tests for ``forge start myproject`` scaffold flow."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()

_PATCH_PATH = "django_forge.cli.start.run_post_install"

# Input patterns:
# Q1 (framework): enter = default (Pure Django)
# Q2 (database):  enter = default (SQLite only)
# Confirm:        Y = yes, N = no
_DEFAULT_INPUT = "\n\n0\nY\n"    # defaults + no layers + confirm
_DEFAULT_ABORT = "\n\n0\nN\n"    # defaults + no layers + abort
_OVERWRITE_OK = "Y\n\n\n0\nY\n" # overwrite + defaults + no layers + confirm


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_start_creates_project_files(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.B — Confirming creates project files."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "myproject"], input=_DEFAULT_INPUT
    )
    assert result.exit_code == 0
    project_dir = tmp_path / "myproject"
    assert project_dir.exists()
    assert (project_dir / "manage.py").exists()
    assert (project_dir / "pyproject.toml").exists()
    assert (
        project_dir / "config" / "settings" / "base.py"
    ).exists()


@patch(_PATCH_PATH, return_value=True)
def test_start_enter_confirms_default(
    _mock_install, tmp_path: Path
) -> None:
    """Pressing Enter accepts all defaults."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "myproject"], input="\n\n0\n\n"
    )
    assert result.exit_code == 0
    assert (tmp_path / "myproject" / "manage.py").exists()


# ---------------------------------------------------------------------------
# User aborts
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_start_abort_on_n(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.K — Pressing N aborts with no files written."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "myproject"], input=_DEFAULT_ABORT
    )
    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    assert not (tmp_path / "myproject").exists()


# ---------------------------------------------------------------------------
# Directory already exists
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_start_existing_directory_n(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.G — When directory exists and user says N, abort."""
    os.chdir(tmp_path)
    (tmp_path / "existing").mkdir()
    result = runner.invoke(
        app, ["start", "existing"], input="N\n"
    )
    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    assert (tmp_path / "existing").exists()


@patch(_PATCH_PATH, return_value=True)
def test_start_existing_directory_y(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.G — When directory exists and user says Y, overwrite."""
    os.chdir(tmp_path)
    (tmp_path / "overwrite_me").mkdir()
    (tmp_path / "overwrite_me" / "old_file.txt").write_text("old")

    result = runner.invoke(
        app, ["start", "overwrite_me"], input=_OVERWRITE_OK
    )
    assert result.exit_code == 0
    assert (tmp_path / "overwrite_me").exists()
    assert not (
        tmp_path / "overwrite_me" / "old_file.txt"
    ).exists()
    assert (
        tmp_path / "overwrite_me" / "manage.py"
    ).exists()


# ---------------------------------------------------------------------------
# Project name in output
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_start_shows_project_name(
    _mock_install, tmp_path: Path
) -> None:
    """Banner shows the project name."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "my-cool-project"], input=_DEFAULT_ABORT
    )
    assert "my-cool-project" in result.stdout


# ---------------------------------------------------------------------------
# Generated file structure
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_generated_files_match_expected(
    _mock_install, tmp_path: Path
) -> None:
    """Generated project has all expected files."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "testproj"], input=_DEFAULT_INPUT
    )
    assert result.exit_code == 0

    expected = [
        "manage.py",
        "pyproject.toml",
        ".env.example",
        ".gitignore",
        "Makefile",
        "config/settings/base.py",
        "config/urls.py",
        "apps/accounts/models.py",
        "apps/accounts/admin.py",
        "apps/accounts/views.py",
        "apps/accounts/api.py",
        "templates/base.html",
        "README.md",
        ".forge.toml",
    ]
    project_dir = tmp_path / "testproj"
    for rel_path in expected:
        file_path = project_dir / rel_path
        assert file_path.exists(), f"Expected {rel_path} to exist"


# ---------------------------------------------------------------------------
# Secret key generation
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_secret_key_in_context(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.L — Secret key is generated and included in rendered files."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "testproj"], input=_DEFAULT_INPUT)
    base_py = (
        tmp_path
        / "testproj"
        / "config"
        / "settings"
        / "base.py"
    ).read_text()
    assert "django-insecure-" in base_py


# ---------------------------------------------------------------------------
# Error handling: extra positional args
# ---------------------------------------------------------------------------


def test_extra_positional_arg_errors() -> None:
    """1.3.M — Extra positional args produce exit code 2."""
    result = runner.invoke(app, ["start", "myproject", "extra"])
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Success banner
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_success_banner_shown(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.F — Success banner prints when install succeeds."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "testproj"], input=_DEFAULT_INPUT
    )
    assert "Next steps" in result.stdout
    assert "Project forged successfully" in result.stdout


# ---------------------------------------------------------------------------
# Installer failure
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=False)
def test_install_failure_message(
    _mock_install, tmp_path: Path
) -> None:
    """When installer fails, no success banner."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "testproj"], input=_DEFAULT_INPUT
    )
    assert "Project forged successfully" not in result.stdout


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_output_uses_rich_styling(
    _mock_install, tmp_path: Path
) -> None:
    """1.3.O — Output includes forge style markers."""
    os.chdir(tmp_path)
    result = runner.invoke(
        app, ["start", "styled"], input=_DEFAULT_INPUT
    )
    assert "FORGE" in result.stdout.upper()
