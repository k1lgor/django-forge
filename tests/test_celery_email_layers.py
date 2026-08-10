"""Tests for Celery and Email optional layers (Story 4.2)."""

import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

CELERY_FILES = ["config/celery.py", "apps/accounts/tasks.py"]

# All 6 framework x database combos with Celery
_FW_AND_DB = [
    ("1", "1", "drf_postgres"),
    ("1", "2", "drf_sqlite"),
    ("2", "1", "ninja_postgres"),
    ("2", "2", "ninja_sqlite"),
    ("3", "1", "pure_postgres"),
    ("3", "2", "pure_sqlite"),
]


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_celery_files_created(_mock_install, fw_in, db_in, suffix, tmp_path) -> None:
    """4.2.A-C - Celery files exist when Celery is selected."""
    os.chdir(tmp_path)
    # Select Celery only
    input_str = f"{fw_in}\n{db_in}\n2\nY\n"
    result = runner.invoke(app, ["start", f"test_{suffix}"], input=input_str)
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / f"test_{suffix}"
    for f in CELERY_FILES:
        assert (project / f).exists(), f"Missing {f} for {suffix}"


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_celery_files_not_created(_mock_install, fw_in, db_in, suffix, tmp_path) -> None:
    """Celery files absent when Celery not selected."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n0\nY\n"
    result = runner.invoke(app, ["start", f"test_no_{suffix}"], input=input_str)
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / f"test_no_{suffix}"
    for f in CELERY_FILES:
        assert not (project / f).exists(), f"Unexpected {f} for {suffix} with no layers"


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_celery_deps_in_pyproject(_mock_install, fw_in, db_in, suffix, tmp_path) -> None:
    """4.2.D - Celery deps present in pyproject.toml."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n2\nY\n"
    runner.invoke(app, ["start", f"test_dep_{suffix}"], input=input_str)
    toml = (tmp_path / f"test_dep_{suffix}" / "pyproject.toml").read_text()
    assert "celery~=5.4.0" in toml
    assert "redis>=" in toml


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_celery_settings_in_base(_mock_install, fw_in, db_in, suffix, tmp_path) -> None:
    """4.2.E-F - Celery settings present in base.py."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n2\nY\n"
    runner.invoke(app, ["start", f"test_set_{suffix}"], input=input_str)
    base = (tmp_path / f"test_set_{suffix}" / "config" / "settings" / "base.py").read_text()
    assert "CELERY_BROKER_URL" in base
    assert "CELERY_RESULT_BACKEND" in base
    assert "CELERY_ACCEPT_CONTENT" in base
    assert "CACHES" in base
    assert "RedisCache" in base


@patch(_PATCH_PATH, return_value=True)
def test_email_settings_in_base(_mock_install, tmp_path) -> None:
    """4.2.G - Email settings present when Email selected."""
    os.chdir(tmp_path)
    input_str = "3\n2\n3\nY\n"  # Pure, SQLite, Email only
    runner.invoke(app, ["start", "test_email"], input=input_str)
    base = (tmp_path / "test_email" / "config" / "settings" / "base.py").read_text()
    assert "EMAIL_BACKEND" in base
    assert "email_host" in base
    assert "email_port" in base


@patch(_PATCH_PATH, return_value=True)
def test_email_settings_not_in_base_when_not_selected(_mock_install, tmp_path) -> None:
    """Email settings absent when Email not selected."""
    os.chdir(tmp_path)
    input_str = "3\n2\n0\nY\n"
    runner.invoke(app, ["start", "test_noemail"], input=input_str)
    base = (tmp_path / "test_noemail" / "config" / "settings" / "base.py").read_text()
    assert "EMAIL_BACKEND" not in base


@patch(_PATCH_PATH, return_value=True)
def test_email_env_vars_in_example(_mock_install, tmp_path) -> None:
    """4.2.H - Email vars in .env.example."""
    os.chdir(tmp_path)
    input_str = "3\n2\n3\nY\n"
    runner.invoke(app, ["start", "test_envmail"], input=input_str)
    env = (tmp_path / "test_envmail" / ".env.example").read_text()
    assert "MAILPIT_SMTP_HOST" in env
    assert "EMAIL_HOST" in env


@patch(_PATCH_PATH, return_value=True)
def test_email_env_vars_not_in_example_when_not_selected(_mock_install, tmp_path) -> None:
    """Email vars absent when Email not selected."""
    os.chdir(tmp_path)
    input_str = "3\n2\n0\nY\n"
    runner.invoke(app, ["start", "test_noenvmail"], input=input_str)
    env = (tmp_path / "test_noenvmail" / ".env.example").read_text()
    assert "MAILPIT_SMTP_HOST" not in env


@patch(_PATCH_PATH, return_value=True)
def test_celery_and_email_together(_mock_install, tmp_path) -> None:
    """4.2.I - Celery+Email simultaneously."""
    os.chdir(tmp_path)
    input_str = "3\n2\n2,3\nY\n"  # Celery + Email
    result = runner.invoke(app, ["start", "test_both"], input=input_str)
    assert result.exit_code == 0, str(result.exception)
    project = tmp_path / "test_both"
    for f in CELERY_FILES:
        assert (project / f).exists(), f"Missing {f} in combo"
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "CELERY_BROKER_URL" in base
    assert "EMAIL_BACKEND" in base
    assert "CACHES" in base


@patch(_PATCH_PATH, return_value=True)
def test_celery_docker_compose_has_redis(_mock_install, tmp_path) -> None:
    """4.2.J - Celery + Docker adds redis to compose."""
    os.chdir(tmp_path)
    input_str = "3\n2\n1,2\nY\n"  # Docker + Celery
    runner.invoke(app, ["start", "test_celerydock"], input=input_str)
    compose = (tmp_path / "test_celerydock" / "compose.yaml").read_text()
    assert "redis:" in compose
    assert "redis:7-alpine" in compose


@patch(_PATCH_PATH, return_value=True)
def test_email_docker_compose_has_mailpit(_mock_install, tmp_path) -> None:
    """4.2.K - Email + Docker adds Mailpit to compose."""
    os.chdir(tmp_path)
    input_str = "3\n2\n1,3\nY\n"  # Docker + Email
    runner.invoke(app, ["start", "test_mailpitdock"], input=input_str)
    compose = (tmp_path / "test_mailpitdock" / "compose.yaml").read_text()
    assert "mailpit:" in compose
    assert "axllent/mailpit" in compose


@patch(_PATCH_PATH, return_value=True)
def test_config_init_has_celery_import_when_selected(_mock_install, tmp_path) -> None:
    """4.2.B - config/__init__.py has celery import."""
    os.chdir(tmp_path)
    input_str = "3\n2\n2\nY\n"
    runner.invoke(app, ["start", "test_celinit"], input=input_str)
    init_py = (tmp_path / "test_celinit" / "config" / "__init__.py").read_text()
    assert "celery_app" in init_py
    assert "from .celery import" in init_py


@patch(_PATCH_PATH, return_value=True)
def test_config_init_no_celery_import_when_not_selected(_mock_install, tmp_path) -> None:
    """config/__init__.py has no celery import when not selected."""
    os.chdir(tmp_path)
    input_str = "3\n2\n0\nY\n"
    runner.invoke(app, ["start", "test_nocelinit"], input=input_str)
    init_py = (tmp_path / "test_nocelinit" / "config" / "__init__.py").read_text()
    assert "celery_app" not in init_py
