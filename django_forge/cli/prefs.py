"""User preference cache for remembering scaffold choices across runs.

Saves the user's framework, database, and layer selections to a JSON file
so the next ``forge start`` can offer them as defaults.

Cache location (all platforms): ``~/.config/forge/prefs.json``
Override via ``FORGE_PREFS_DIR`` env var.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any


def _prefs_file() -> Path:
    """Return the path to the preferences JSON file.

    All platforms use ``~/.config/forge/prefs.json``.
    Override via ``FORGE_PREFS_DIR`` env var.
    """
    env_override = os.environ.get("FORGE_PREFS_DIR")
    if env_override:
        return Path(env_override) / "prefs.json"

    return Path.home() / ".config" / "forge" / "prefs.json"


def _default_prefs() -> dict[str, Any]:
    """Return the fallback defaults (matching the base scaffold context)."""
    return {
        "api": "drf",
        "db": "postgres",
        "layers": [],
    }


def save_prefs(*, api: str, db: str, layers: list[str]) -> None:
    """Persist the user's scaffold choices to disk.

    No-op if the directory cannot be created (permissions, read-only FS, etc.).

    Args:
        api: Framework choice (``"drf"``, ``"ninja"``, or ``"pure"``).
        db: Database choice (``"postgres"`` or ``"sqlite"``).
        layers: List of layer names (e.g., ``["docker", "celery"]``).
    """
    prefs_file = _prefs_file()
    try:
        prefs_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    data: dict[str, Any] = {
        "api": api,
        "db": db,
        "layers": list(layers),
    }
    with contextlib.suppress(OSError):
        # disk full, permissions, etc.
        prefs_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_prefs() -> dict[str, Any]:
    """Load cached preferences from disk.

    Returns the defaults (DRF, PostgreSQL, no layers) if the cache file
    does not exist, is unreadable, or contains invalid data.
    """
    prefs_file = _prefs_file()
    if not prefs_file.exists():
        return _default_prefs()

    try:
        raw = prefs_file.read_text(encoding="utf-8")
    except OSError:
        return _default_prefs()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _default_prefs()

    # Validate keys — only accept known keys, ignore extras
    result = _default_prefs()
    if isinstance(data.get("api"), str) and data["api"] in ("drf", "ninja", "pure"):
        result["api"] = data["api"]
    if isinstance(data.get("db"), str) and data["db"] in ("postgres", "sqlite"):
        result["db"] = data["db"]
    if isinstance(data.get("layers"), list):
        valid = [
            layer
            for layer in data["layers"]
            if isinstance(layer, str)
            and layer in ("docker", "celery", "email", "cache", "social", "storage")
        ]
        result["layers"] = valid

    return result
