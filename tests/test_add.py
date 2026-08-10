"""Tests for ``forge add`` — adding optional layers to existing projects."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.main import app

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_forge_project(tmp_path: Path) -> None:
    """Create a minimal forge project with .forge.toml and key files."""
    (tmp_path / "manage.py").write_text("# manage.py")
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "settings").mkdir(parents=True, exist_ok=True)

    _make_forge_toml(tmp_path, ["drf", "postgres", []])


def _make_forge_toml(
    tmp_path: Path,
    config: tuple,
) -> None:
    """Write a .forge.toml with given config."""
    api, db, layers = config
    layers_str = ", ".join(f'"{layer}"' for layer in layers)
    toml = f'[forge]\nversion = "0.1.0"\napi = "{api}"\ndb = "{db}"\nlayers = [{layers_str}]\n'
    (tmp_path / ".forge.toml").write_text(toml)


# ---------------------------------------------------------------------------
# 6.1.A — Project detection
# ---------------------------------------------------------------------------


def test_add_detects_project_from_forge_toml(tmp_path: Path) -> None:
    """6.1.A — forge add reads .forge.toml and parses context."""
    _make_forge_toml(tmp_path, ("drf", "postgres", []))
    from django_forge.cli.add import _detect_project

    context = _detect_project(tmp_path)
    assert context is not None
    assert context["api"] == "drf"
    assert context["db"] == "postgres"
    assert context["layers"] == []


# ---------------------------------------------------------------------------
# 6.1.B — Non-forge project error
# ---------------------------------------------------------------------------


def test_add_non_forge_project_error(tmp_path: Path) -> None:
    """6.1.B — forge add outside a forge project shows error."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "docker"])
    assert result.exit_code == 0
    assert "Not a forge project" in result.stdout


# ---------------------------------------------------------------------------
# 6.1.F — Already installed
# ---------------------------------------------------------------------------


def test_add_docker_already_installed(tmp_path: Path) -> None:
    """6.1.F — forge add docker on a project with Docker shows message."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", ["docker"]))
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "docker"])
    assert result.exit_code == 0
    assert "already installed" in result.stdout


# ---------------------------------------------------------------------------
# 6.1.G — Unknown layer
# ---------------------------------------------------------------------------


def test_add_unknown_layer(tmp_path: Path) -> None:
    """6.1.G — Unknown layer name shows error."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "foo"])
    assert result.exit_code == 0
    assert "Unknown layer" in result.stdout
    assert "docker" in result.stdout
    assert "celery" in result.stdout
    assert "email" in result.stdout


# ---------------------------------------------------------------------------
# 6.1.C + 6.1.E — Docker files created + .forge.toml updated
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_add_docker_creates_files_and_updates_toml(_mock_install, tmp_path: Path) -> None:
    """6.1.C+E — forge add docker creates files and updates .forge.toml."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", []))
    os.chdir(tmp_path)

    result = runner.invoke(app, ["add", "docker"])
    assert result.exit_code == 0, str(result.exception)
    assert "Added" in result.stdout
    assert "docker" in result.stdout

    # Docker files should exist
    assert (tmp_path / "Dockerfile").exists()
    assert (tmp_path / "compose.yaml").exists()
    assert (tmp_path / ".dockerignore").exists()

    # .forge.toml should be updated
    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert "docker" in toml["forge"]["layers"]


# ---------------------------------------------------------------------------
# 6.1.E — Preserves existing layers
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_add_docker_preserves_existing_layers(_mock_install, tmp_path: Path) -> None:
    """6.1.E — .forge.toml preserves existing layers when adding new ones."""
    _make_forge_toml(tmp_path, ("drf", "postgres", ["celery"]))
    os.chdir(tmp_path)
    runner.invoke(app, ["add", "docker"])
    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    layers = toml["forge"]["layers"]
    assert "celery" in layers
    assert "docker" in layers


# ---------------------------------------------------------------------------
# 6.1.D — Overwrite prompt (simulate via empty project dir)
# ---------------------------------------------------------------------------


def test_add_docker_overwrite_prompt(tmp_path: Path) -> None:
    """6.1.D — Existing Dockerfile triggers overwrite prompt."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", []))
    (tmp_path / "Dockerfile").write_text("# old content")
    os.chdir(tmp_path)

    # Input "N" = don't overwrite
    result = runner.invoke(app, ["add", "docker"], input="N\n")
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 6.1.I — Handler dispatch
# ---------------------------------------------------------------------------


def test_add_celery_handled_when_no_forge_project(tmp_path: Path) -> None:
    """Non-forge project error also works for celery."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "celery"])
    assert result.exit_code == 0
    assert "Not a forge project" in result.stdout


def test_add_email_handled_when_no_forge_project(tmp_path: Path) -> None:
    """Non-forge project error also works for email."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["add", "email"])
    assert result.exit_code == 0
    assert "Not a forge project" in result.stdout


# ---------------------------------------------------------------------------
# _update_forge_toml unit test
# ---------------------------------------------------------------------------


def test_update_forge_toml_preserves_api_and_db(tmp_path: Path) -> None:
    """_update_forge_toml preserves api and db values."""
    _make_forge_toml(tmp_path, ("ninja", "postgres", ["docker"]))
    from django_forge.cli.add import _update_forge_toml

    _update_forge_toml(tmp_path / ".forge.toml", ["docker", "celery"])
    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert toml["forge"]["api"] == "ninja"
    assert toml["forge"]["db"] == "postgres"
    assert "celery" in toml["forge"]["layers"]
    assert "docker" in toml["forge"]["layers"]


# ---------------------------------------------------------------------------
# 6.2 — forge add celery creates Celery files
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_add_celery_creates_celery_files(_mock_install, tmp_path) -> None:
    """6.2.A — forge add celery creates celery.py and tasks.py."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", []))
    # Create a minimal project structure
    (tmp_path / "manage.py").write_text("# manage")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "__init__.py").write_text("# config")
    (tmp_path / "config" / "settings").mkdir()
    (tmp_path / "config" / "settings" / "base.py").write_text("# django settings")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    os.chdir(tmp_path)

    # Answer Y to the overwrite prompt
    result = runner.invoke(app, ["add", "celery"], input="Y\n")
    assert result.exit_code == 0
    assert (tmp_path / "config" / "celery.py").exists()
    assert (tmp_path / "apps" / "accounts" / "tasks.py").exists()

    # .forge.toml should be updated
    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert "celery" in toml["forge"]["layers"]


@patch(_PATCH_PATH, return_value=True)
def test_add_email_creates_env_vars(_mock_install, tmp_path) -> None:
    """6.2.F-I — forge add email adds email vars to .env.example."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", []))
    (tmp_path / "manage.py").write_text("# manage")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings").mkdir()
    (tmp_path / "config" / "settings" / "base.py").write_text("# django settings")
    (tmp_path / "config" / "settings" / "dev.py").write_text("# dev settings")
    (tmp_path / "config" / "settings" / "prod.py").write_text("# prod settings")
    (tmp_path / ".env.example").write_text("# env")
    os.chdir(tmp_path)

    result = runner.invoke(app, ["add", "email"], input="Y\n")
    assert result.exit_code == 0

    # Email vars should be in .env.example
    env_content = (tmp_path / ".env.example").read_text()
    assert "EMAIL_HOST" in env_content

    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert "email" in toml["forge"]["layers"]


@patch(_PATCH_PATH, return_value=True)
def test_add_celery_after_docker_updates_compose(_mock_install, tmp_path) -> None:
    """6.2.K — Celery after Docker re-renders compose with redis."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", ["docker"]))
    (tmp_path / "manage.py").write_text("# manage")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "__init__.py").write_text("# config")
    (tmp_path / "config" / "settings").mkdir()
    (tmp_path / "config" / "settings" / "base.py").write_text("# django settings")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "compose.yaml").write_text("services:\n  app:\n")
    os.chdir(tmp_path)

    result = runner.invoke(app, ["add", "celery"], input="Y\n")
    assert result.exit_code == 0

    compose = (tmp_path / "compose.yaml").read_text()
    assert "redis:" in compose


@patch(_PATCH_PATH, return_value=True)
def test_add_email_declined_no_files_changed(_mock_install, tmp_path) -> None:
    """6.2.B — Declining overwrite leaves files unchanged."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", []))
    (tmp_path / "manage.py").write_text("# manage")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings").mkdir()
    (tmp_path / "config" / "settings" / "base.py").write_text("# ORIGINAL base")
    (tmp_path / ".env.example").write_text("# ORIGINAL env")
    os.chdir(tmp_path)

    # Input N = don't overwrite
    result = runner.invoke(app, ["add", "email"], input="N\n")
    assert result.exit_code == 0
    assert (tmp_path / ".env.example").read_text() == "# ORIGINAL env", (
        "File should remain unchanged"
    )

    # .forge.toml should NOT be updated
    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert "email" not in toml["forge"]["layers"]


@patch(_PATCH_PATH, return_value=True)
def test_add_celery_then_docker_order_independence(_mock_install, tmp_path) -> None:
    """6.2.M — Celery then Docker works (order independence)."""
    _make_forge_toml(tmp_path, ("pure", "sqlite", []))
    (tmp_path / "manage.py").write_text("# manage")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "__init__.py").write_text("# config")
    (tmp_path / "config" / "settings").mkdir()
    (tmp_path / "config" / "settings" / "base.py").write_text("# django settings")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    os.chdir(tmp_path)

    # Add celery first
    r1 = runner.invoke(app, ["add", "celery"], input="Y\n")
    assert r1.exit_code == 0
    assert (tmp_path / "config" / "celery.py").exists()

    # Then add docker
    r2 = runner.invoke(app, ["add", "docker"])
    assert r2.exit_code == 0
    assert (tmp_path / "Dockerfile").exists()

    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert "celery" in toml["forge"]["layers"]
    assert "docker" in toml["forge"]["layers"]
