"""Shared project detection, identity and context building for the CLI.

``detect_project`` / ``build_context`` replace the three hand-built copies in
``cli/add.py``, ``cli/upgrade.py`` and ``cli/prompts.py`` that had already
diverged in their defaults (design entry 36).
"""

from __future__ import annotations

import re
from pathlib import Path

from django_forge import __version__ as _forge_version
from django_forge.cli.console import console
from django_forge.registry import LAYERS

try:  # Python 3.11+
    import tomllib  # ty: ignore[unresolved-import]  (stdlib 3.11+; project supports 3.10)
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

# The eleven optional layer ids, derived from the single registry
# (design entry 35); ``build_context`` writes one ``has_*`` flag per entry.
LAYER_IDS: tuple[str, ...] = tuple(layer.id for layer in LAYERS)


def _slugify(name: str) -> str:
    """Project-name to slug: dashes and spaces become underscores."""
    return name.replace("-", "_").replace(" ", "_")


def detect_project(project_dir: Path) -> dict | None:
    """Read ``.forge.toml`` and return the project state dict.

    Returns ``None`` when the file is missing, unreadable, unparseable or has
    no ``[forge]`` section — always printing the concrete reason (parse errors
    include the parser message instead of a generic "corrupted" claim).
    """
    project_dir = Path(project_dir)
    forge_toml = project_dir / ".forge.toml"
    if not forge_toml.exists():
        console.print()
        console.print("  [forge.error]Not a forge project.[/]")
        console.print(
            "  [forge.muted]Run [forge.highlight]forge-django start myproject[/] first.[/]"
        )
        return None
    try:
        raw = forge_toml.read_text(encoding="utf-8")
    except OSError as exc:
        console.print()
        console.print(f"  [forge.error]Cannot read .forge.toml: {exc}[/]")
        return None
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        console.print()
        console.print(f"  [forge.error]Invalid .forge.toml: {exc}[/]")
        return None
    section = data.get("forge")
    if not isinstance(section, dict) or not section:
        console.print()
        console.print("  [forge.error]Invalid .forge.toml: no \\[forge] section.[/]")
        return None
    name = section.get("project_name") or project_dir.name
    slug = section.get("project_slug") or _slugify(name)
    return {
        "api": section.get("api", "drf"),
        "db": section.get("db", "postgres"),
        "layers": list(section.get("layers", [])),
        "project_name": name,
        "project_slug": slug,
    }


def read_identity(project_dir: Path) -> tuple[str, str]:
    """``(project_name, project_slug)`` from ``.forge.toml``.

    Files written before 0.4 lack the identity keys — fall back to the
    directory name so upgrades of older projects keep working.
    """
    project_dir = Path(project_dir)
    forge_toml = project_dir / ".forge.toml"
    if forge_toml.exists():
        try:
            data = tomllib.loads(forge_toml.read_text(encoding="utf-8"))
            section = data.get("forge", {})
            if isinstance(section, dict):
                name = section.get("project_name") or project_dir.name
                slug = section.get("project_slug") or _slugify(name)
                return str(name), str(slug)
        except (tomllib.TOMLDecodeError, OSError):
            pass
    name = project_dir.name
    return name, _slugify(name)


def write_identity(project_dir: Path, project_name: str, project_slug: str) -> None:
    """Set ``project_name`` / ``project_slug`` in ``[forge]``, preserving the rest."""
    _patch_forge_section(
        Path(project_dir) / ".forge.toml",
        {"project_name": f'"{project_name}"', "project_slug": f'"{project_slug}"'},
    )


def update_layers(path: Path, layers: list[str]) -> None:
    """Update ``layers`` (and ``version``) in ``[forge]`` — textually.

    Patches only the matching key lines inside the ``[forge]`` table: comments,
    key order and any other tables stay byte-identical (design entry 36 /
    Alternative H — no serialization round-trip, no extra dependency).
    ``layers`` is stored sorted+deduplicated, matching the previous behaviour.
    """
    ordered = sorted(set(layers))
    value = "[" + ", ".join(f'"{layer}"' for layer in ordered) + "]"
    _patch_forge_section(
        Path(path),
        {"layers": value, "version": f'"{_forge_version}"'},
    )


def _patch_forge_section(path: Path, updates: dict[str, str]) -> None:
    """Replace ``key = ...`` lines inside ``[forge]`` (or insert them)."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "[forge]")
    except StopIteration as exc:
        raise ValueError(f"{path.name}: no [forge] section to update") from exc
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")),
        len(lines),
    )
    for key, formatted in updates.items():
        replaced = False
        for i in range(start + 1, end):
            stripped = lines[i].lstrip()
            if stripped.startswith(key) and stripped[len(key) :].lstrip().startswith("="):
                match = re.match(
                    rf"(\s*{re.escape(key)}\s*=\s*)(.+?)(\s+#.*)?$",
                    lines[i].rstrip("\n"),
                )
                prefix = match.group(1) if match else f"{key} = "
                comment = (match.group(3) or "") if match else ""
                newline = "\n" if lines[i].endswith("\n") else ""
                lines[i] = f"{prefix}{formatted}{comment}{newline}"
                replaced = True
                break
        if not replaced:
            lines.insert(start + 1, f"{key} = {formatted}\n")
            end += 1
    path.write_text("".join(lines), encoding="utf-8")


def build_context(state: dict) -> dict:
    """The single render-context builder (was copied three times).

    *state* carries ``project_name`` (required), optional ``project_slug`` and
    ``api`` / ``db`` / ``layers`` from :func:`detect_project` or the wizard.
    ``secret_key`` starts empty — callers that persist a secret overwrite it
    after building (``add`` / ``upgrade`` recovery, ``start`` generation).
    """
    project_name = str(state.get("project_name") or "")
    project_slug = str(state.get("project_slug") or _slugify(project_name))
    api = state.get("api") or "drf"
    db = state.get("db") or "postgres"
    layers = list(state.get("layers") or [])

    context: dict = {
        "project_name": project_name,
        "project_slug": project_slug,
        "secret_key": "",
        "api": api,
        "db": db,
        "layers": layers,
        "use_drf": api == "drf",
        "use_ninja": api == "ninja",
        "use_pure_django": api == "pure",
        "forge_version": _forge_version,
    }
    for layer in LAYERS:
        context[layer.has_flag] = layer.id in layers
    return context
