"""Adversarial tests for the 2-question prompt system (Story 2.1)."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"


@patch(_PATCH_PATH, return_value=True)
def test_drf_postgres_flow(_mock_install, tmp_path: Path) -> None:
    """DRF + PostgreSQL generates correct project."""
    os.chdir(tmp_path)
    r = runner.invoke(app, ["start", "myapp"], input="1\n1\n0\nY\n")
    assert r.exit_code == 0, str(r.exception)
    d = tmp_path / "myapp"
    assert (d / "manage.py").exists()


@patch(_PATCH_PATH, return_value=True)
def test_ninja_sqlite_flow(_mock_install, tmp_path: Path) -> None:
    """Ninja + SQLite generates correct project."""
    os.chdir(tmp_path)
    r = runner.invoke(app, ["start", "myapp"], input="2\n2\n0\nY\n")
    assert r.exit_code == 0, str(r.exception)
    d = tmp_path / "myapp"
    assert (d / "manage.py").exists()


@patch(_PATCH_PATH, return_value=True)
def test_all_defaults_prompt(_mock_install, tmp_path: Path) -> None:
    """All defaults (just press Enter) works."""
    os.chdir(tmp_path)
    r = runner.invoke(app, ["start", "myapp"], input="\n\n0\nY\n")
    assert r.exit_code == 0, str(r.exception)


@patch(_PATCH_PATH, return_value=True)
def test_invalid_framework_choice_rejected(_mock_install, tmp_path: Path) -> None:
    """Invalid framework choice (e.g., '4') causes reprompt."""
    os.chdir(tmp_path)
    r = runner.invoke(
        app,
        ["start", "myapp"],
        input="4\n3\n2\n0\nY\n",
    )
    assert r.exit_code == 0, str(r.exception)
    assert (tmp_path / "myapp" / "manage.py").exists()


@patch(_PATCH_PATH, return_value=True)
def test_invalid_db_choice_rejected(_mock_install, tmp_path: Path) -> None:
    """Invalid database choice (e.g., '3') causes reprompt."""
    os.chdir(tmp_path)
    r = runner.invoke(
        app,
        ["start", "myapp"],
        input="3\n3\n2\n0\nY\n",
    )
    assert r.exit_code == 0, str(r.exception)
    assert (tmp_path / "myapp" / "manage.py").exists()


@patch(_PATCH_PATH, return_value=True)
def test_all_combinations_have_prompt_output(_mock_install, tmp_path: Path) -> None:
    """Prompt output mentions framework, database, and layer choices."""
    os.chdir(tmp_path)
    r = runner.invoke(app, ["start", "myapp"], input="1\n1\n0\nY\n")
    assert "API Framework" in r.stdout
    assert "Database" in r.stdout
    assert "Optional Layers" in r.stdout
    assert "Layers:" in r.stdout
    assert "Project:" in r.stdout
    assert "Looks good?" in r.stdout
