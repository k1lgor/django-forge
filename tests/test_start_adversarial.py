"""Adversarial edge-case tests for the scaffold flow (Epics 1-3) and --no-input (Epic 5)."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.installer import (
    _check_uv_installed,
    _truncate,
    run_post_install,
)
from django_forge.cli.main import app
from django_forge.cli.start import (
    _generate_secret_key,
    _handle_existing_directory,
)

runner = CliRunner()
_PATCH_INSTALL = "django_forge.cli.start.run_post_install"

# Input: accept defaults (framework=3/Pure, database=2/SQLite, layers=0) then confirm
_DEFAULT_OK = "3\n2\n0\nY\n"
_DEFAULT_OK_ENTER = "\n\n0\n\n"  # all defaults + no layers + confirm

# ---------------------------------------------------------------------------
# Secret key generation
# ---------------------------------------------------------------------------


def test_secret_key_length() -> None:
    key = _generate_secret_key()
    assert key.startswith("django-insecure-")
    assert len(key) >= 66


def test_secret_key_uniqueness() -> None:
    keys = {_generate_secret_key() for _ in range(100)}
    assert len(keys) == 100


# ---------------------------------------------------------------------------
# Truncate utility
# ---------------------------------------------------------------------------


def test_truncate_short_text() -> None:
    assert _truncate("hello", 100) == "hello"


def test_truncate_long_text() -> None:
    long_text = "line1\nline2\nline3\nline4"
    result = _truncate(long_text, 15)
    assert len(result) < len(long_text)
    assert result.endswith("...")


def test_truncate_empty() -> None:
    assert _truncate("", 100) == ""


# ---------------------------------------------------------------------------
# _check_uv_installed
# ---------------------------------------------------------------------------


@patch("shutil.which", return_value="/usr/local/bin/uv")
def test_check_uv_installed_found(_mock_which) -> None:
    assert _check_uv_installed("testproj") is True


@patch("shutil.which", return_value=None)
def test_check_uv_installed_not_found(_mock_which) -> None:
    assert _check_uv_installed("testproj") is False


# ---------------------------------------------------------------------------
# _handle_existing_directory
# ---------------------------------------------------------------------------


def test_handle_existing_aborts_on_invalid_input(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "mydir").mkdir()
    monkeypatch.setattr("builtins.input", lambda _: "invalid\n")
    result = _handle_existing_directory(tmp_path / "mydir")
    assert result is False
    assert (tmp_path / "mydir").exists()


# ---------------------------------------------------------------------------
# Start with edge-case project names
# ---------------------------------------------------------------------------


@patch(_PATCH_INSTALL, return_value=True)
def test_start_project_name_with_dots(_mock_install, tmp_path: Path) -> None:
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "my.project"], input=_DEFAULT_OK)
    assert result.exit_code == 0
    assert (tmp_path / "my.project" / "manage.py").exists()


@patch(_PATCH_INSTALL, return_value=True)
def test_start_project_name_with_underscores(_mock_install, tmp_path: Path) -> None:
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "my_project"], input=_DEFAULT_OK)
    assert result.exit_code == 0
    assert (tmp_path / "my_project" / "manage.py").exists()


@patch(_PATCH_INSTALL, return_value=True)
def test_start_project_name_starts_with_number(_mock_install, tmp_path: Path) -> None:
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "42project"], input=_DEFAULT_OK)
    assert result.exit_code == 0
    assert (tmp_path / "42project" / "manage.py").exists()


# ---------------------------------------------------------------------------
# Consecutive start calls
# ---------------------------------------------------------------------------


@patch(_PATCH_INSTALL, return_value=True)
def test_start_twice_in_same_dir_overwrite(_mock_install, tmp_path: Path) -> None:
    os.chdir(tmp_path)
    r1 = runner.invoke(app, ["start", "myapp"], input=_DEFAULT_OK)
    assert r1.exit_code == 0
    assert (tmp_path / "myapp" / "manage.py").exists()

    r2 = runner.invoke(app, ["start", "myapp"], input="Y\n3\n2\n0\nY\n")
    assert r2.exit_code == 0
    assert (tmp_path / "myapp" / "manage.py").exists()


# ---------------------------------------------------------------------------
# --no-input mode (Epic 5)
# ---------------------------------------------------------------------------


@patch(_PATCH_INSTALL, return_value=True)
def test_no_input_scaffolds_without_prompts(_mock_install, tmp_path: Path) -> None:
    """5.1.D - --no-input skips all prompts and generates project."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj", "--no-input"])
    assert result.exit_code == 0
    assert (tmp_path / "testproj" / "manage.py").exists()


@patch(_PATCH_INSTALL, return_value=True)
def test_no_input_shows_default_banner(_mock_install, tmp_path: Path) -> None:
    """5.1.D - --no-input prints the using-defaults message."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj", "--no-input"])
    assert "Using defaults" in result.stdout
    assert "--no-input mode" in result.stdout


@patch(_PATCH_INSTALL, return_value=True)
def test_no_input_uses_drf_defaults(_mock_install, tmp_path: Path) -> None:
    """5.1.E - --no-input uses DRF + PostgreSQL defaults."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "testproj", "--no-input"])
    pyproject = (tmp_path / "testproj" / "pyproject.toml").read_text()
    assert "djangorestframework" in pyproject


@patch(_PATCH_INSTALL, return_value=True)
def test_no_input_skips_confirm_prompt(_mock_install, tmp_path: Path) -> None:
    """5.1.F - --no-input skips the Looks good? confirmation."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj", "--no-input"])
    assert "Looks good?" not in result.stdout


# ---------------------------------------------------------------------------
# CI env auto-detection
# ---------------------------------------------------------------------------


@patch(_PATCH_INSTALL, return_value=True)
def test_ci_env_activates_no_input(_mock_install, monkeypatch, tmp_path) -> None:
    """5.1.G - CI=true activates no-input without --no-input flag."""
    monkeypatch.setenv("CI", "true")
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj"])
    assert result.exit_code == 0
    assert (tmp_path / "testproj" / "manage.py").exists()
    assert "CI mode detected" in result.stdout


@patch(_PATCH_INSTALL, return_value=True)
def test_github_actions_env_activates_no_input(_mock_install, monkeypatch, tmp_path) -> None:
    """5.1.H - GITHUB_ACTIONS=true activates no-input."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj"])
    assert result.exit_code == 0
    assert (tmp_path / "testproj" / "manage.py").exists()
    assert "CI mode detected" in result.stdout


# ---------------------------------------------------------------------------
# run_post_install edge cases
# ---------------------------------------------------------------------------


def test_run_post_install_nonexistent_dir() -> None:
    result = run_post_install(Path("/nonexistent/project"))
    assert result is False


# ---------------------------------------------------------------------------
# Secret key Jinja2 safety
# ---------------------------------------------------------------------------


def test_secret_key_no_jinja_conflict() -> None:
    for _ in range(500):
        key = _generate_secret_key()
        assert "{{" not in key
        assert "}}" not in key


# ---------------------------------------------------------------------------
# Empty project name rejected
# ---------------------------------------------------------------------------


def test_start_rejects_empty_name() -> None:
    """Empty project name is refused with a clear message."""
    result = runner.invoke(app, ["start", ""])
    assert result.exit_code == 0
    assert "cannot be empty" in result.stdout


# ---------------------------------------------------------------------------
# "y" lowercase confirms
# ---------------------------------------------------------------------------


@patch(_PATCH_INSTALL, return_value=True)
def test_start_confirm_with_y(_mock_install, tmp_path: Path) -> None:
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj"], input="3\n2\n0\ny\n")
    assert result.exit_code == 0
    assert (tmp_path / "testproj" / "manage.py").exists()


# ---------------------------------------------------------------------------
# N at confirmation aborts
# ---------------------------------------------------------------------------


@patch(_PATCH_INSTALL, return_value=True)
def test_start_abort_with_n_at_confirm(_mock_install, tmp_path: Path) -> None:
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "testproj"], input="3\n2\n0\nN\n")
    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    assert not (tmp_path / "testproj").exists()
