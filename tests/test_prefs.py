"""Unit tests for the user preference cache (prefs.py)."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from django_forge.cli.prefs import _prefs_file, load_prefs, save_prefs


class TestPrefsFile:
    """Unified config path resolution — all platforms use ~/.config/forge/."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_path(self, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: Path("/home/testuser"))
        result = _prefs_file()
        assert result == Path("/home/testuser/.config/forge/prefs.json")

    @patch.dict(os.environ, {}, clear=True)
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows path semantics")
    def test_windows_path(self, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Users\testuser"))
        result = _prefs_file()
        assert result == Path(r"C:\Users\testuser\.config\forge\prefs.json")

    @patch.dict(os.environ, {}, clear=True)
    def test_macos_path(self, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: Path("/Users/testuser"))
        result = _prefs_file()
        assert result == Path("/Users/testuser/.config/forge/prefs.json")

    @patch.dict(os.environ, {"FORGE_PREFS_DIR": "/tmp/myforge"}, clear=True)
    def test_env_override_takes_priority(self, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: Path("/home/testuser"))
        result = _prefs_file()
        assert result == Path("/tmp/myforge/prefs.json")


class TestSaveLoad:
    """Round-trip save and load."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "prefs.json"
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            save_prefs(api="ninja", db="sqlite", layers=["docker", "email"])
            loaded = load_prefs()
            assert loaded["api"] == "ninja"
            assert loaded["db"] == "sqlite"
            assert loaded["layers"] == ["docker", "email"]

    def test_load_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "nonexistent.json"
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            loaded = load_prefs()
            assert loaded["api"] == "drf"
            assert loaded["db"] == "postgres"
            assert loaded["layers"] == []

    def test_load_returns_defaults_on_corrupt_json(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text("not valid json{", encoding="utf-8")
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            loaded = load_prefs()
            assert loaded["api"] == "drf"

    def test_load_rejects_invalid_api_value(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text(
            json.dumps({"api": "graphql", "db": "postgres", "layers": []}),
            encoding="utf-8",
        )
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            loaded = load_prefs()
            assert loaded["api"] == "drf"

    def test_load_rejects_invalid_db_value(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text(
            json.dumps({"api": "drf", "db": "oracle", "layers": []}),
            encoding="utf-8",
        )
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            loaded = load_prefs()
            assert loaded["db"] == "postgres"

    def test_load_filters_invalid_layer_names(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text(
            json.dumps({"api": "drf", "db": "sqlite", "layers": ["docker", "k8s", "celery"]}),
            encoding="utf-8",
        )
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            loaded = load_prefs()
            assert loaded["layers"] == ["docker", "celery"]

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "deeply" / "nested" / "prefs.json"
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            save_prefs(api="pure", db="sqlite", layers=[])
            assert prefs_file.exists()
            data = json.loads(prefs_file.read_text(encoding="utf-8"))
            assert data["api"] == "pure"

    def test_overwrite_updates_existing(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "prefs.json"
        with patch("django_forge.cli.prefs._prefs_file", return_value=prefs_file):
            save_prefs(api="drf", db="postgres", layers=["docker"])
            save_prefs(api="ninja", db="sqlite", layers=[])
            loaded = load_prefs()
            assert loaded["api"] == "ninja"
            assert loaded["db"] == "sqlite"
            assert loaded["layers"] == []
