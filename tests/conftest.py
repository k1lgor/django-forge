"""Shared pytest fixtures for django-forge tests."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_prefs(tmp_path: Path) -> None:
    """Redirect the preference cache to a temp directory per test.

    Prevents real ``~/.config/forge/prefs.json`` from leaking into tests
    and ensures every test starts with a clean slate.
    """
    os.environ["FORGE_PREFS_DIR"] = str(tmp_path / "forge_prefs")


@pytest.fixture(autouse=True)
def _no_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip CI environment markers so ``forge start`` stays interactive.

    GitHub Actions sets ``CI``/``GITHUB_ACTIONS``, which auto-activates
    forge's no-input mode and silently ignores the wizard answers the
    tests pipe in. Tests that exercise CI detection set these explicitly.
    """
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
