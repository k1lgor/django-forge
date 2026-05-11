"""Tests for django-debug-toolbar and forge upgrade."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge.cli.main import app
from django_forge.renderer import Renderer

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

PROJECT_TEMPLATES = Path(__file__).resolve().parent.parent / "django_forge" / "templates"
MINIMAL_CONTEXT = {
    "project_name": "testproj",
    "project_slug": "testproj",
    "secret_key": "test-key-123",
    "api": "pure",
    "db": "sqlite",
    "layers": [],
    "use_drf": False,
    "use_ninja": False,
    "use_pure_django": True,
    "has_docker": False,
    "has_celery": False,
    "has_email": False,
}


# ---------------------------------------------------------------------------
# django-debug-toolbar
# ---------------------------------------------------------------------------


def test_dev_py_has_debug_toolbar() -> None:
    """dev.py.j2 renders with debug_toolbar settings."""
    renderer = Renderer(PROJECT_TEMPLATES)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        dev = (target / "config" / "settings" / "dev.py").read_text()
        assert "debug_toolbar" in dev
        assert "DebugToolbarMiddleware" in dev
        assert "INTERNAL_IPS" in dev
        assert "127.0.0.1" in dev


def test_urls_py_has_debug_toolbar() -> None:
    """urls.py.j2 renders with debug toolbar URL."""
    renderer = Renderer(PROJECT_TEMPLATES)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        urls = (target / "config" / "urls.py").read_text()
        assert "debug_toolbar" in urls
        assert "__debug__" in urls


def test_pyproject_has_debug_toolbar_dep() -> None:
    """pyproject.toml.j2 has django-debug-toolbar dev dep."""
    renderer = Renderer(PROJECT_TEMPLATES)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        toml = (target / "pyproject.toml").read_text()
        assert "django-debug-toolbar" in toml


# ---------------------------------------------------------------------------
# forge upgrade
# ---------------------------------------------------------------------------


def test_upgrade_help() -> None:
    """forge upgrade --help shows help."""
    result = runner.invoke(app, ["upgrade", "--help"])
    assert result.exit_code == 0
    assert "Re-apply" in result.stdout or "upgrade" in result.stdout.lower()


def test_upgrade_non_forge_project(tmp_path: Path) -> None:
    """forge upgrade outside a forge project shows error."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["upgrade"])
    assert result.exit_code == 0
    assert "Not a forge project" in result.stdout


def _write_forge_toml(path: Path, layers: list[str]) -> None:
    """Write a minimal .forge.toml in the given directory."""
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
def test_upgrade_with_forge_project(
    _mock_install, tmp_path: Path
) -> None:
    """forge upgrade on a forge project re-renders templates."""
    _write_forge_toml(tmp_path, [])
    (tmp_path / "manage.py").write_text("# old manage.py content")
    (tmp_path / "config" / "settings").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "__init__.py").write_text("# old")
    (tmp_path / "config" / "settings" / "base.py").write_text(
        "# old base"
    )
    os.chdir(tmp_path)

    result = runner.invoke(app, ["upgrade"], input="Y\n")
    assert result.exit_code == 0, str(result.exception)
    assert "Upgraded" in result.stdout or "upgraded" in result.stdout


@patch(_PATCH_PATH, return_value=True)
def test_upgrade_declined_leaves_files(
    _mock_install, tmp_path: Path
) -> None:
    """forge upgrade declined leaves files unchanged."""
    _write_forge_toml(tmp_path, [])
    (tmp_path / "manage.py").write_text("# OLD")
    (tmp_path / "config" / "settings").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "__init__.py").write_text("# OLD")
    (tmp_path / "config" / "settings" / "base.py").write_text(
        "# OLD base"
    )
    os.chdir(tmp_path)

    result = runner.invoke(app, ["upgrade"], input="N\n")
    assert result.exit_code == 0
    assert (
        tmp_path / "manage.py"
    ).read_text() == "# OLD", "File should remain unchanged"


_DEFAULT_OK = "3\n2\n0\nY\n"


@patch(_PATCH_PATH, return_value=True)
def test_upgrade_end_to_end(
    _mock_install, tmp_path: Path
) -> None:
    """E2E: forge start --no-input -> upgrade -> verify version."""
    os.chdir(tmp_path)
    r1 = runner.invoke(
        app, ["start", "testproj", "--no-input"]
    )
    assert r1.exit_code == 0, str(r1.exception)
    project = tmp_path / "testproj"

    os.chdir(project)

    r2 = runner.invoke(app, ["upgrade"], input="Y\n")
    assert r2.exit_code == 0, str(r2.exception)

    import tomli
    toml = tomli.loads((project / ".forge.toml").read_text())
    assert "forge" in toml
