"""Adversarial QA for debug-toolbar, forge upgrade, and regressions."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"


# ---------------------------------------------------------------------------
# forge upgrade — edge cases
# ---------------------------------------------------------------------------


def _make_forge_toml(path: Path, layers: list[str]) -> None:
    layers_str = ", ".join(f'"{layer}"' for layer in layers)
    toml = (
        f'[forge]\n'
        f'version = "0.2.0"\n'
        f'api = "pure"\n'
        f'db = "sqlite"\n'
        f'layers = [{layers_str}]\n'
    )
    (path / ".forge.toml").write_text(toml)


@patch(_PATCH_PATH, return_value=True)
def test_upgrade_no_config_dir(
    _mock_install, tmp_path: Path
) -> None:
    """Upgrade on project with no config/ dir still works."""
    _make_forge_toml(tmp_path, [])
    (tmp_path / "manage.py").write_text("# old")
    os.chdir(tmp_path)
    result = runner.invoke(app, ["upgrade"], input="N\n")
    assert result.exit_code == 0


@patch(_PATCH_PATH, return_value=True)
def test_upgrade_all_layers(
    _mock_install, tmp_path: Path
) -> None:
    """Upgrade on project with all 3 layers already."""
    _make_forge_toml(tmp_path, ["docker", "celery", "email"])
    (tmp_path / "manage.py").write_text("# old")
    (tmp_path / "config" / "settings").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "__init__.py").write_text("# config")
    (tmp_path / "config" / "settings" / "base.py").write_text(
        "# base"
    )
    os.chdir(tmp_path)
    result = runner.invoke(app, ["upgrade"], input="Y\n")
    assert result.exit_code == 0, str(result.exception)


def test_upgrade_empty_project(tmp_path: Path) -> None:
    """Upgrade with .forge.toml but no other files still works."""
    _make_forge_toml(tmp_path, [])
    os.chdir(tmp_path)
    result = runner.invoke(app, ["upgrade"])
    assert result.exit_code == 0


def test_upgrade_missing_toml(tmp_path: Path) -> None:
    """Upgrade with no .forge.toml at all."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["upgrade"])
    assert result.exit_code == 0
    assert "Not a forge project" in result.stdout


# ---------------------------------------------------------------------------
# forge add — still works after template changes
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_add_docker_still_works(
    _mock_install, tmp_path: Path
) -> None:
    """forge add docker still works after template changes."""
    _make_forge_toml(tmp_path, [])
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "docker"])
    assert result.exit_code == 0
    assert (tmp_path / "Dockerfile").exists()


@patch(_PATCH_PATH, return_value=True)
def test_add_celery_still_works(
    _mock_install, tmp_path: Path
) -> None:
    """forge add celery still works."""
    _make_forge_toml(tmp_path, [])
    (tmp_path / "manage.py").write_text("# m")
    (tmp_path / "config" / "settings").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "__init__.py").write_text("# c")
    (tmp_path / "config" / "settings" / "base.py").write_text("# s")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "celery"], input="Y\n")
    assert result.exit_code == 0, str(result.exception)
    assert (tmp_path / "config" / "celery.py").exists()


# ---------------------------------------------------------------------------
# forge list — still works
# ---------------------------------------------------------------------------


def test_forge_list_still_works() -> None:
    """forge list still produces output."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Available Frameworks" in result.stdout
    assert "Available Optional Layers" in result.stdout
    assert "Core Layers" in result.stdout


# ---------------------------------------------------------------------------
# Generated project structure verification
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_generated_project_has_debug_toolbar_in_settings(
    _mock_install, tmp_path: Path
) -> None:
    """Generated project dev.py has debug_toolbar config."""
    os.chdir(tmp_path)
    r1 = runner.invoke(
        app, ["start", "testproj", "--no-input"]
    )
    assert r1.exit_code == 0, str(r1.exception)
    project = tmp_path / "testproj"
    dev = (project / "config" / "settings" / "dev.py").read_text()
    assert "debug_toolbar" in dev
    assert "DebugToolbarMiddleware" in dev


@patch(_PATCH_PATH, return_value=True)
def test_generated_project_has_debug_toolbar_in_urls(
    _mock_install, tmp_path: Path
) -> None:
    """Generated project urls.py has debug toolbar URL."""
    os.chdir(tmp_path)
    r1 = runner.invoke(
        app, ["start", "testproj", "--no-input"]
    )
    assert r1.exit_code == 0, str(r1.exception)
    project = tmp_path / "testproj"
    urls = (project / "config" / "urls.py").read_text()
    assert "debug_toolbar" in urls


# ---------------------------------------------------------------------------
# forge version
# ---------------------------------------------------------------------------


def test_forge_version() -> None:
    """forge --version works."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "forge" in result.stdout.lower()
    assert "0" in result.stdout
