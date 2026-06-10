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
