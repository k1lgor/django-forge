"""Regression tests for acceptance criteria gaps found during QA.

Covers:
- 4.2.L: All 24 framework x database x Celery x Email combos render
- 5.1.J: forge list --help shows help text
- Edge cases for --no-input mode
"""

import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

# All 6 framework+db combos
FW_DB_COMBOS = [
    ("drf", "postgres", "1", "1"),
    ("drf", "sqlite", "1", "2"),
    ("ninja", "postgres", "2", "1"),
    ("ninja", "sqlite", "2", "2"),
    ("pure", "postgres", "3", "1"),
    ("pure", "sqlite", "3", "2"),
]


@pytest.mark.parametrize("api,db,fw_in,db_in", FW_DB_COMBOS)
@patch(_PATCH_PATH, return_value=True)
def test_all_24_combos_render(
    _mock_install, api, db, fw_in, db_in, tmp_path
) -> None:
    """4.2.L — 24 combos (6 fw+db x 2 Celery x 2 Email) render without error."""
    for use_celery in (False, True):
        for use_email in (False, True):
            layer_parts = []
            if use_celery:
                layer_parts.append("2")
            if use_email:
                layer_parts.append("3")
            layer_input = ",".join(layer_parts) if layer_parts else "0"
            project_name = (
                f"t_{api}_{db}"
                f"{'_cel' if use_celery else ''}"
                f"{'_eml' if use_email else ''}"
            )
            os.chdir(tmp_path)
            input_str = f"{fw_in}\n{db_in}\n{layer_input}\nY\n"
            result = runner.invoke(
                app, ["start", project_name], input=input_str
            )
            assert result.exit_code == 0, (
                f"Failed for {project_name}: {result.exception}"
            )
            project = tmp_path / project_name
            pyproject = (project / "pyproject.toml").read_text()
            if use_celery:
                assert "celery~=5.4.0" in pyproject, (
                    f"Missing celery dep for {project_name}"
                )
            else:
                assert "celery~=5.4.0" not in pyproject, (
                    f"Unexpected celery dep for {project_name}"
                )


@patch(_PATCH_PATH, return_value=True)
def test_no_input_refuses_existing_dir(
    _mock_install, tmp_path
) -> None:
    """--no-input must refuse to overwrite an existing directory."""
    os.chdir(tmp_path)
    (tmp_path / "mydir").mkdir()
    (tmp_path / "mydir" / "old.txt").write_text("old")
    result = runner.invoke(
        app, ["start", "mydir", "--no-input"]
    )
    assert result.exit_code == 0
    assert "Refusing" in result.stdout
    assert not (tmp_path / "mydir" / "manage.py").exists()
    assert (tmp_path / "mydir" / "old.txt").exists()


def test_forge_list_help() -> None:
    """5.1.J — forge list --help shows help text."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "Show available frameworks" in result.stdout


def test_forge_start_help_shows_no_input() -> None:
    """5.1.K — forge start --help shows --no-input flag."""
    result = runner.invoke(app, ["start", "--help"])
    assert result.exit_code == 0
    assert "--no-input" in result.stdout
