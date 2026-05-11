"""Tests for Docker optional layer (Story 4.1)."""

import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

# Combos: all 6 framework x database with Docker on/off
_FW_AND_DB = [
    ("drf", "postgres", "1", "1"),
    ("drf", "sqlite", "1", "2"),
    ("ninja", "postgres", "2", "1"),
    ("ninja", "sqlite", "2", "2"),
    ("pure", "postgres", "3", "1"),
    ("pure", "sqlite", "3", "2"),
]

DOCKER_FILES = ["Dockerfile", "compose.yaml", ".dockerignore"]


@pytest.mark.parametrize("api,db,fw_in,db_in", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_docker_files_created_when_selected(
    _mock_install, api, db, fw_in, db_in, tmp_path
) -> None:
    """4.1.D-F - Docker files exist when Docker is selected."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n1\nY\n"  # 1=Docker
    result = runner.invoke(
        app, ["start", f"test_{api}_{db}"], input=input_str
    )
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / f"test_{api}_{db}"
    for f in DOCKER_FILES:
        assert (project / f).exists(), f"Missing {f} for {api}+{db}"


@pytest.mark.parametrize("api,db,fw_in,db_in", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_docker_files_not_created_when_not_selected(
    _mock_install, api, db, fw_in, db_in, tmp_path
) -> None:
    """4.1.L - Docker files absent when Docker is NOT selected."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n0\nY\n"  # 0 = no layers
    result = runner.invoke(
        app, ["start", f"test_no_{api}_{db}"], input=input_str
    )
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / f"test_no_{api}_{db}"
    for f in DOCKER_FILES:
        assert not (project / f).exists(), (
            f"Unexpected {f} for {api}+{db} with no layers"
        )


@patch(_PATCH_PATH, return_value=True)
def test_celery_email_no_files_without_docker(
    _mock_install, tmp_path
) -> None:
    """4.1.I - Celery/Email selected but no files generated."""
    os.chdir(tmp_path)
    # Select Celery (2) + Email (3), NO Docker
    input_str = "3\n2\n2,3\nY\n"
    result = runner.invoke(
        app, ["start", "test_celery_email"], input=input_str
    )
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / "test_celery_email"
    # Docker files should NOT exist
    for f in DOCKER_FILES:
        assert not (project / f).exists(), (
            f"Unexpected {f} when only Celery+Email selected"
        )


@patch(_PATCH_PATH, return_value=True)
def test_multi_layer_selection(
    _mock_install, tmp_path
) -> None:
    """Selecting Docker + Celery generates Docker files."""
    os.chdir(tmp_path)
    # Select Docker (1) + Celery (2), no Email
    input_str = "3\n2\n1,2\nY\n"
    result = runner.invoke(
        app, ["start", "test_multi"], input=input_str
    )
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / "test_multi"
    for f in DOCKER_FILES:
        assert (project / f).exists(), f"Missing {f} in multi-layer"


@patch(_PATCH_PATH, return_value=True)
def test_docker_env_var_in_env_example(
    _mock_install, tmp_path
) -> None:
    """4.1.H - Docker env var present when Docker selected."""
    os.chdir(tmp_path)
    input_str = "3\n2\n1\nY\n"
    runner.invoke(
        app, ["start", "test_dockerenv"], input=input_str
    )
    env = (
        tmp_path / "test_dockerenv" / ".env.example"
    ).read_text()
    assert "DOCKER=true" in env


@patch(_PATCH_PATH, return_value=True)
def test_docker_env_var_not_in_env_example_without_docker(
    _mock_install, tmp_path
) -> None:
    """DOCKER=true absent when Docker not selected."""
    os.chdir(tmp_path)
    input_str = "3\n2\n0\nY\n"
    runner.invoke(
        app, ["start", "test_noenv"], input=input_str
    )
    env = (
        tmp_path / "test_noenv" / ".env.example"
    ).read_text()
    assert "DOCKER=true" not in env
