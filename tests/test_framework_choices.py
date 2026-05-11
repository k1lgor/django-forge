"""Tests for all 6 framework x database combinations (Story 2.1)."""

import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

# Input mapping:
# Q1 (framework): 1=DRF, 2=Ninja, 3=Pure
# Q2 (database):  1=PostgreSQL, 2=SQLite
# Q3 (layers):    0=none
# Confirm:        Y

COMBOS = [
    # (name, framework_input, db_input, api_value, db_value)
    ("drf_postgres", "1", "1", "drf", "postgres"),
    ("drf_sqlite", "1", "2", "drf", "sqlite"),
    ("ninja_postgres", "2", "1", "ninja", "postgres"),
    ("ninja_sqlite", "2", "2", "ninja", "sqlite"),
    ("pure_postgres", "3", "1", "pure", "postgres"),
    ("pure_sqlite", "3", "2", "pure", "sqlite"),
]


@pytest.mark.parametrize("name,fw_input,db_input,api,db", COMBOS)
@patch(_PATCH_PATH, return_value=True)
def test_framework_db_combo(
    _mock_install, name, fw_input, db_input, api, db, tmp_path
) -> None:
    """2.1.K - forge start works with each framework+db combo."""
    os.chdir(tmp_path)
    input_str = f"{fw_input}\n{db_input}\n0\nY\n"
    result = runner.invoke(
        app, ["start", f"test_{name}"], input=input_str
    )
    assert result.exit_code == 0, (
        f"Failed for {name} (fw={api}, db={db}): "
        f"{result.exception}"
    )
    project_dir = tmp_path / f"test_{name}"
    assert (project_dir / "manage.py").exists()
    assert (
        project_dir / "apps" / "accounts" / "models.py"
    ).exists()


@pytest.mark.parametrize("name,fw_input,db_input,api,db", COMBOS)
@patch(_PATCH_PATH, return_value=True)
def test_framework_db_pyproject_has_correct_deps(
    _mock_install, name, fw_input, db_input, api, db, tmp_path
) -> None:
    """2.1.D-G - pyproject.toml has correct deps for each combo."""
    _ = db
    os.chdir(tmp_path)
    input_str = f"{fw_input}\n{db_input}\n0\nY\n"
    runner.invoke(app, ["start", f"test_{name}"], input=input_str)
    toml = (
        tmp_path / f"test_{name}" / "pyproject.toml"
    ).read_text()

    if api == "drf":
        assert "djangorestframework" in toml
        assert "djangorestframework-simplejwt" in toml
    elif api == "ninja":
        assert "django-ninja" in toml
    else:
        assert "djangorestframework" not in toml
        assert "django-ninja" not in toml
        assert "django-allauth" in toml


@pytest.mark.parametrize("name,fw_input,db_input,api,db", COMBOS)
@patch(_PATCH_PATH, return_value=True)
def test_framework_db_settings_has_correct_config(
    _mock_install, name, fw_input, db_input, api, db, tmp_path
) -> None:
    """2.1.D-G - base.py has correct config for each combo."""
    os.chdir(tmp_path)
    input_str = f"{fw_input}\n{db_input}\n0\nY\n"
    runner.invoke(app, ["start", f"test_{name}"], input=input_str)
    base_py = (
        tmp_path
        / f"test_{name}"
        / "config"
        / "settings"
        / "base.py"
    ).read_text()

    if api == "drf":
        assert '"rest_framework"' in base_py
    if db == "postgres":
        assert "postgresql" in base_py or "postgres" in base_py.lower()
