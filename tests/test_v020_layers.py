"""Tests for the v0.2 caching, social auth, and S3 storage layers."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

_FW_AND_DB = [
    ("1", "1", "drf_postgres"),
    ("1", "2", "drf_sqlite"),
    ("2", "1", "ninja_postgres"),
    ("2", "2", "ninja_sqlite"),
    ("3", "1", "pure_postgres"),
    ("3", "2", "pure_sqlite"),
]


# ---------------------------------------------------------------------------
# Caching layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_cache_layer_adds_redis_dep(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Caching layer adds redis dependency when selected without celery."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n4\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    toml = (tmp_path / f"t_{suffix}" / "pyproject.toml").read_text()
    assert "redis>=" in toml


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_cache_layer_adds_caches_setting(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Caching layer adds CACHES config to base.py."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n4\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    base = (tmp_path / f"t_{suffix}" / "config" / "settings" / "base.py").read_text()
    assert "CACHES" in base
    assert "RedisCache" in base


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_cache_layer_adds_cache_redis_url_setting(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Caching layer adds cache_redis_url to Settings class."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n4\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    base = (tmp_path / f"t_{suffix}" / "config" / "settings" / "base.py").read_text()
    assert "cache_redis_url" in base


@patch(_PATCH_PATH, return_value=True)
def test_cache_layer_not_added_when_not_selected(
    _mock_install, tmp_path: Path
) -> None:
    """CACHES config absent when caching not selected."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n0\nY\n")
    base = (tmp_path / "t" / "config" / "settings" / "base.py").read_text()
    assert "CACHES" not in base


@patch(_PATCH_PATH, return_value=True)
def test_cache_layer_compose_redis_when_docker(
    _mock_install, tmp_path: Path
) -> None:
    """Redis service in compose when cache + docker selected."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n1,4\nY\n")
    compose = (tmp_path / "t" / "compose.yaml").read_text()
    assert "redis:" in compose


# ---------------------------------------------------------------------------
# Social auth layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_social_layer_adds_providers_setting(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Social auth layer adds SOCIALACCOUNT_PROVIDERS to base.py."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n5\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    base = (tmp_path / f"t_{suffix}" / "config" / "settings" / "base.py").read_text()
    assert "SOCIALACCOUNT_PROVIDERS" in base
    assert '"google"' in base
    assert '"github"' in base


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_social_layer_adds_env_vars(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Social auth layer adds provider env vars to .env.example."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n5\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    env = (tmp_path / f"t_{suffix}" / ".env.example").read_text()
    assert "GOOGLE_CLIENT_ID" in env
    assert "GITHUB_CLIENT_ID" in env


@patch(_PATCH_PATH, return_value=True)
def test_social_layer_not_added_when_not_selected(
    _mock_install, tmp_path: Path
) -> None:
    """SOCIALACCOUNT_PROVIDERS absent when social not selected."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n0\nY\n")
    base = (tmp_path / "t" / "config" / "settings" / "base.py").read_text()
    assert "SOCIALACCOUNT_PROVIDERS" not in base


# ---------------------------------------------------------------------------
# S3 Storage layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_storage_layer_adds_django_storages_dep(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Storage layer adds django-storages[s3] dependency."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n6\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    toml = (tmp_path / f"t_{suffix}" / "pyproject.toml").read_text()
    assert "django-storages" in toml


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_storage_layer_adds_s3_settings(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Storage layer adds S3 settings to base.py."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n6\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    base = (tmp_path / f"t_{suffix}" / "config" / "settings" / "base.py").read_text()
    assert "AWS_ACCESS_KEY_ID" in base
    assert "storages.backends.s3.S3Storage" in base


@pytest.mark.parametrize("fw_in,db_in,suffix", _FW_AND_DB)
@patch(_PATCH_PATH, return_value=True)
def test_storage_layer_adds_env_vars(
    _mock_install, fw_in, db_in, suffix, tmp_path: Path
) -> None:
    """Storage layer adds S3 env vars to .env.example."""
    os.chdir(tmp_path)
    input_str = f"{fw_in}\n{db_in}\n6\nY\n"
    runner.invoke(app, ["start", f"t_{suffix}"], input=input_str)
    env = (tmp_path / f"t_{suffix}" / ".env.example").read_text()
    assert "AWS_STORAGE_BUCKET_NAME" in env


@patch(_PATCH_PATH, return_value=True)
def test_storage_layer_not_added_when_not_selected(
    _mock_install, tmp_path: Path
) -> None:
    """S3 storage absent when storage not selected."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n0\nY\n")
    base = (tmp_path / "t" / "config" / "settings" / "base.py").read_text()
    assert "storages.backends.s3" not in base


# ---------------------------------------------------------------------------
# All layers together
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_all_six_layers_together(
    _mock_install, tmp_path: Path
) -> None:
    """All layers can be selected together without conflicts."""
    os.chdir(tmp_path)
    runner.invoke(
        app, ["start", "t"], input="1\n1\n1,2,3,4,5,6\nY\n"
    )
    project = tmp_path / "t"
    assert (project / "pyproject.toml").exists()
    # Should contain deps from all layers
    toml = (project / "pyproject.toml").read_text()
    assert "djangorestframework" in toml
    assert "redis>=" in toml
    assert "django-storages" in toml
    assert "celery~=5.4.0" in toml


# ---------------------------------------------------------------------------
# forge add for new layers — successful additions
# ---------------------------------------------------------------------------


def _start_and_cd(tmp_path: Path) -> Path:
    """Scaffold a project and chdir into it."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n0\nY\n")
    project = tmp_path / "t"
    os.chdir(project)
    return project


@patch(_PATCH_PATH, return_value=True)
def test_add_cache_adds_caches_to_base(
    _mock_install, tmp_path: Path
) -> None:
    """forge add cache adds CACHES config to base.py."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "cache"], input="Y\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "CACHES" in base
    assert "RedisCache" in base


@patch(_PATCH_PATH, return_value=True)
def test_add_cache_adds_redis_dep(
    _mock_install, tmp_path: Path
) -> None:
    """forge add cache adds redis dependency."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "cache"], input="Y\n")
    toml = (project / "pyproject.toml").read_text()
    assert "redis>=" in toml


@patch(_PATCH_PATH, return_value=True)
def test_add_cache_updates_forge_toml(
    _mock_install, tmp_path: Path
) -> None:
    """forge add cache adds 'cache' to .forge.toml layers."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "cache"], input="Y\n")
    import tomli
    data = tomli.loads((project / ".forge.toml").read_text())
    assert "cache" in data["forge"]["layers"]


@patch(_PATCH_PATH, return_value=True)
def test_add_social_adds_providers(
    _mock_install, tmp_path: Path
) -> None:
    """forge add social adds SOCIALACCOUNT_PROVIDERS to base.py."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "social"], input="Y\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "SOCIALACCOUNT_PROVIDERS" in base
    assert '"google"' in base


@patch(_PATCH_PATH, return_value=True)
def test_add_social_adds_env_vars(
    _mock_install, tmp_path: Path
) -> None:
    """forge add social adds provider env vars to .env.example."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "social"], input="Y\n")
    env = (project / ".env.example").read_text()
    assert "GOOGLE_CLIENT_ID" in env
    assert "GITHUB_CLIENT_SECRET" in env


@patch(_PATCH_PATH, return_value=True)
def test_add_storage_adds_s3_backend(
    _mock_install, tmp_path: Path
) -> None:
    """forge add storage adds S3 storage backend to base.py."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "storage"], input="Y\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "storages.backends.s3.S3Storage" in base
    assert "AWS_ACCESS_KEY_ID" in base


@patch(_PATCH_PATH, return_value=True)
def test_add_storage_adds_dep(
    _mock_install, tmp_path: Path
) -> None:
    """forge add storage adds django-storages[s3] dependency."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "storage"], input="Y\n")
    toml = (project / "pyproject.toml").read_text()
    assert "django-storages" in toml


@patch(_PATCH_PATH, return_value=True)
def test_add_storage_adds_env_vars(
    _mock_install, tmp_path: Path
) -> None:
    """forge add storage adds S3 env vars to .env.example."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "storage"], input="Y\n")
    env = (project / ".env.example").read_text()
    assert "AWS_STORAGE_BUCKET_NAME" in env


# ---------------------------------------------------------------------------
# Integration — multiple forge add calls
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_add_multiple_layers_sequentially(
    _mock_install, tmp_path: Path
) -> None:
    """Multiple forge add calls accumulate layers in .forge.toml."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "cache"], input="Y\n")
    runner.invoke(app, ["add", "social"], input="Y\n")
    runner.invoke(app, ["add", "storage"], input="Y\n")
    import tomli
    data = tomli.loads((project / ".forge.toml").read_text())
    layers = data["forge"]["layers"]
    assert "cache" in layers
    assert "social" in layers
    assert "storage" in layers


@patch(_PATCH_PATH, return_value=True)
def test_add_then_start_preserves_context(
    _mock_install, tmp_path: Path
) -> None:
    """forge add cache, then forge add social — both present in context."""
    project = _start_and_cd(tmp_path)
    runner.invoke(app, ["add", "cache"], input="Y\n")
    runner.invoke(app, ["add", "social"], input="Y\n")
    base = (project / "config" / "settings" / "base.py").read_text()
    assert "CACHES" in base
    assert "SOCIALACCOUNT_PROVIDERS" in base


# ---------------------------------------------------------------------------
# Error and edge cases (kept from original)
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
@patch("django_forge.cli.add._confirm_existing_files", return_value=False)
def test_add_cache_declined_no_files_changed(
    mock_confirm, _mock_install, tmp_path: Path
) -> None:
    """forge add cache declined leaves no files changed."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n0\nY\n")
    os.chdir(tmp_path / "t")
    result = runner.invoke(app, ["add", "cache"])
    assert result.exit_code == 0
    assert "No files were changed" in result.stdout


@patch(_PATCH_PATH, return_value=True)
def test_add_unknown_layer_error(
    _mock_install, tmp_path: Path
) -> None:
    """Unknown layer shows error for forge add."""
    os.chdir(tmp_path)
    runner.invoke(app, ["start", "t"], input="\n\n0\nY\n")
    os.chdir(tmp_path / "t")
    result = runner.invoke(app, ["add", "graphql"])
    assert "Unknown layer" in result.stdout


@patch(_PATCH_PATH, return_value=True)
def test_add_on_non_forge_project(
    _mock_install, tmp_path: Path
) -> None:
    """forge add on non-forge project shows error."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "social"])
    assert (
        "Run forge start myproject first" in result.stdout
        or "Not a forge project" in result.stdout
    )
