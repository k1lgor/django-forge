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


# ---------------------------------------------------------------------------
# 0.4 prompt contract: invalid layer numbers re-prompt, Enter keeps the cache
# ---------------------------------------------------------------------------


@patch(_PATCH_PATH, return_value=True)
def test_invalid_layer_selection_reprompts(_mock_install, tmp_path: Path) -> None:
    """An out-of-range layer number re-prompts instead of being dropped."""
    os.chdir(tmp_path)
    r = runner.invoke(app, ["start", "myapp"], input="1\n1\n99\n0\nY\n")
    assert r.exit_code == 0, str(r.exception)
    assert "Invalid selection" in r.stdout
    assert (tmp_path / "myapp" / "manage.py").exists()
    toml = (tmp_path / "myapp" / ".forge.toml").read_text()
    assert "layers = []" in toml


@patch(_PATCH_PATH, return_value=True)
@patch(
    "django_forge.cli.prompts.load_prefs",
    return_value={"api": "pure", "db": "sqlite", "layers": ["cache"]},
)
def test_layers_prompt_defaults_to_cached_selection(
    _mock_load, _mock_install, monkeypatch, tmp_path: Path
) -> None:
    """Enter on the layers prompt accepts the cached selection (comma numbers)."""
    # Keep the preference write inside this test's temp dir.
    monkeypatch.setenv("FORGE_PREFS_DIR", str(tmp_path / "prefs"))
    os.chdir(tmp_path)
    # Enter x4: framework, database, layers (default "4"), summary confirm.
    r = runner.invoke(app, ["start", "myapp"], input="\n\n\n\n")
    assert r.exit_code == 0, str(r.exception)
    assert "● Caching" in r.stdout
    assert (tmp_path / "myapp" / "config" / "settings" / "base.py").read_text().count("CACHES") >= 1
    toml = (tmp_path / "myapp" / ".forge.toml").read_text()
    assert '"cache"' in toml
