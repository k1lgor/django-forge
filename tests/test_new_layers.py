"""Tests for the v0.3 optional layers: healthcheck, audit, backup, seed, preflight."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

# All five new layers selected in the wizard (Pure Django, SQLite)
_ALL_NEW = "3\n2\n7,8,9,10,11\nY\n"


def _start_and_cd(tmp_path: Path, layer_input: str = "\n\n0\nY\n") -> Path:
    """Scaffold a project and chdir into it."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input=layer_input)
    project = tmp_path / "t"
    os.chdir(project)
    return project


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_start_healthcheck_wires_apps_and_url(_mock_install, tmp_path: Path) -> None:
    """Wizard selection wires health_check apps, /healthz URL, and the dep."""
    project = _start_and_cd(tmp_path, _ALL_NEW)
    base = (project / "config" / "settings" / "base.py").read_text()
    assert '"health_check",' in base
    assert '"health_check.db",' in base
    urls = (project / "config" / "urls.py").read_text()
    assert 'path("healthz/", include("health_check.urls"))' in urls
    toml = (project / "pyproject.toml").read_text()
    assert "django-health-check" in toml


@patch(_PATCH_PATH, return_value=True)
def test_healthcheck_omits_cache_check_without_redis(_mock_install, tmp_path: Path) -> None:
    """Without cache/celery layers, no cache check is registered."""
    project = _start_and_cd(tmp_path, "\n\n7\nY\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "health_check.cache" not in base
    assert "celery_ping" not in base


@patch(_PATCH_PATH, return_value=True)
def test_add_healthcheck_to_existing_project(_mock_install, tmp_path: Path) -> None:
    """forge add healthcheck wires the layer into an existing project."""
    project = _start_and_cd(tmp_path)
    result = runner.invoke(app, ["add", "healthcheck"], input="Y\n")
    assert result.exit_code == 0, str(result.exception)
    base = (project / "config" / "settings" / "base.py").read_text()
    assert '"health_check",' in base
    assert (
        'path("healthz/", include("health_check.urls"))'
        in (project / "config" / "urls.py").read_text()
    )
    # health-check ships a table-bearing app — the user must be told to migrate.
    assert "uv run manage.py migrate" in result.stdout


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_audit_wires_history_on_user(_mock_install, tmp_path: Path) -> None:
    """Audit layer adds HistoricalRecords, app, middleware, and admin."""
    project = _start_and_cd(tmp_path, "\n\n8\nY\n")
    models = (project / "apps" / "accounts" / "models.py").read_text()
    assert "HistoricalRecords" in models
    assert "history = HistoricalRecords()" in models
    base = (project / "config" / "settings" / "base.py").read_text()
    assert '"simple_history",' in base
    assert "simple_history.middleware.HistoryRequestMiddleware" in base
    admin = (project / "apps" / "accounts" / "admin.py").read_text()
    assert "SimpleHistoryAdmin" in admin
    toml = (project / "pyproject.toml").read_text()
    assert "django-simple-history" in toml


@patch(_PATCH_PATH, return_value=True)
def test_audit_absent_without_layer(_mock_install, tmp_path: Path) -> None:
    """No audit code in generated files without the layer."""
    project = _start_and_cd(tmp_path)
    models = (project / "apps" / "accounts" / "models.py").read_text()
    assert "HistoricalRecords" not in models
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "simple_history" not in base


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_backup_local_storage_and_targets(_mock_install, tmp_path: Path) -> None:
    """Backup layer configures local storage, dep, and Makefile targets."""
    project = _start_and_cd(tmp_path, "\n\n9\nY\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert '"dbbackup",' in base
    assert "DBBACKUP_STORAGE" in base
    assert "FileSystemStorage" in base
    toml = (project / "pyproject.toml").read_text()
    assert "django-dbbackup" in toml
    makefile = (project / "Makefile").read_text()
    assert "backup:" in makefile
    assert "restore:" in makefile


@patch(_PATCH_PATH, return_value=True)
def test_backup_uses_s3_when_storage_layer_present(_mock_install, tmp_path: Path) -> None:
    """Backup + storage layers reuse the configured S3 backend."""
    project = _start_and_cd(tmp_path, "\n\n6,9\nY\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert 'DBBACKUP_STORAGE = STORAGES["default"]["BACKEND"]' in base
    assert "storages.backends.s3.S3Storage" in base
    assert "FileSystemStorage" not in base


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_seed_ships_factory_and_command(_mock_install, tmp_path: Path) -> None:
    """Seed layer ships factories.py, seed command, and Makefile target."""
    project = _start_and_cd(tmp_path, "\n\n10\nY\n")
    assert (project / "apps" / "accounts" / "factories.py").exists()
    seed_cmd = project / "apps" / "accounts" / "management" / "commands" / "seed.py"
    assert seed_cmd.exists()
    src = seed_cmd.read_text()
    assert "UserFactory" in src
    assert "add_arguments" in src
    makefile = (project / "Makefile").read_text()
    assert "seed:" in makefile


@patch(_PATCH_PATH, return_value=True)
def test_seed_absent_without_layer(_mock_install, tmp_path: Path) -> None:
    """No factories or seed command without the layer."""
    project = _start_and_cd(tmp_path)
    assert not (project / "apps" / "accounts" / "factories.py").exists()
    assert not (project / "apps" / "accounts" / "management" / "commands" / "seed.py").exists()


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_preflight_ships_command(_mock_install, tmp_path: Path) -> None:
    """Preflight layer ships the preflight command and Makefile target."""
    project = _start_and_cd(tmp_path, "\n\n11\nY\n")
    cmd = project / "apps" / "accounts" / "management" / "commands" / "preflight.py"
    assert cmd.exists()
    src = cmd.read_text()
    assert "check" in src
    assert "makemigrations" in src
    assert "migrate" in src
    makefile = (project / "Makefile").read_text()
    assert "preflight:" in makefile


@patch(_PATCH_PATH, return_value=True)
def test_preflight_absent_without_layer(_mock_install, tmp_path: Path) -> None:
    """No preflight command without the layer."""
    project = _start_and_cd(tmp_path)
    assert not (project / "apps" / "accounts" / "management" / "commands" / "preflight.py").exists()


# ---------------------------------------------------------------------------
# Cross-cutting: forge add + forge upgrade on the new layers
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_add_all_five_new_layers_sequentially(_mock_install, tmp_path: Path) -> None:
    """forge add works for each new layer on an existing project."""
    project = _start_and_cd(tmp_path)
    for layer in ["healthcheck", "audit", "backup", "seed", "preflight"]:
        result = runner.invoke(app, ["add", layer], input="Y\n")
        assert result.exit_code == 0, str(result.exception)
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "health_check" in base
    assert "simple_history" in base
    assert "dbbackup" in base
    assert (project / "apps" / "accounts" / "factories.py").exists()
    assert (project / "apps" / "accounts" / "management" / "commands" / "preflight.py").exists()
    import tomli

    data = tomli.loads((project / ".forge.toml").read_text())
    for layer in ("healthcheck", "audit", "backup", "seed", "preflight"):
        assert layer in data["forge"]["layers"]


@patch(_PATCH_PATH, return_value=True)
def test_upgrade_preserves_new_layer_flags(_mock_install, tmp_path: Path) -> None:
    """forge upgrade keeps the new layer code in rendered files."""
    project = _start_and_cd(tmp_path, _ALL_NEW)
    before = (project / "apps" / "accounts" / "models.py").read_text()
    result = runner.invoke(app, ["upgrade"], input="Y\n")
    assert result.exit_code == 0, str(result.exception)
    after = (project / "apps" / "accounts" / "models.py").read_text()
    assert "HistoricalRecords" in after
    assert before == after  # pristine files re-render byte-identical


def test_unknown_new_layer_still_rejected(tmp_path: Path) -> None:
    """Unknown layer names are still rejected."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "quantum"])
    assert result.exit_code == 0
    assert "Unknown layer" in result.stdout
