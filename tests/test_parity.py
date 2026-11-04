"""Cross-artifact consistency: name, install command, repo URL, version.

Design entry 44 — closes B1/M5/M12 mechanically. Cells where an artifact does
not carry the value are skipped BY NAME (absent values are not failures);
any present cell whose value has drifted from the canonical one fails.
"""

import re
from pathlib import Path

import tomli as tomllib  # dev dep mirrors stdlib tomllib (Python 3.10)

import django_forge

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = "forge-django"
INSTALL_CMD = "uv tool install forge-django"
REPO_URL = "https://github.com/k1lgor/django-forge"

skipped: list[str] = []


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_optional(rel: str) -> str | None:
    """Read *rel*, or None when the artifact is not shipped (site/ in an sdist)."""
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.exists() else None


def _version() -> str:
    data = tomllib.loads(_read("pyproject.toml"))
    return data["project"]["version"]


def test_distribution_name_parity() -> None:
    """Every artifact that carries the distribution name says forge-django."""
    data = tomllib.loads(_read("pyproject.toml"))
    assert data["project"]["name"] == DIST_NAME

    readme = _read("README.md")
    installs = re.findall(r"uv tool install\s+([A-Za-z0-9_.-]+)", readme)
    assert installs, "README has no install command"
    for found in installs:
        assert found == DIST_NAME, f"README installs {found!r}, not {DIST_NAME}"

    site_html = _read_optional("site/index.html")
    if site_html is None:
        skipped.append("distribution name: site/index.html (artifact absent)")
    else:
        for found in re.findall(r"uv tool install\s+([A-Za-z0-9_.-]+)", site_html):
            assert found == DIST_NAME, f"site/index.html installs {found!r}"

    data_js = _read_optional("site/src/lib/forge-data.js")
    if data_js is None:
        skipped.append("distribution name: site/src/lib/forge-data.js (artifact absent)")
    else:
        match = re.search(r'INSTALL_CMD\s*=\s*"uv tool install\s+([^"]+)"', data_js)
        assert match, "forge-data.js has no INSTALL_CMD"
        assert match.group(1) == DIST_NAME, match.group(1)
        run = re.search(r'RUN_CMD\s*=\s*"([^"]+)"', data_js)
        assert run, "forge-data.js has no RUN_CMD"
        assert run.group(1).startswith(DIST_NAME + " "), run.group(1)

    # Generated README carries the rename note / upgrade command.
    template_readme = _read("django_forge/templates/README.md.j2")
    assert f"{DIST_NAME} upgrade" in template_readme


def test_install_command_parity() -> None:
    """README, site index and forge-data.js all ship the same install line."""
    assert INSTALL_CMD in _read("README.md"), f"README.md lacks {INSTALL_CMD!r}"
    site_html = _read_optional("site/index.html")
    if site_html is None:
        skipped.append("install command: site/index.html (artifact absent)")
    else:
        assert INSTALL_CMD in site_html, f"site/index.html lacks {INSTALL_CMD!r}"
    data_js = _read_optional("site/src/lib/forge-data.js")
    if data_js is None:
        skipped.append("install command: site/src/lib/forge-data.js (artifact absent)")
    else:
        assert f'INSTALL_CMD = "{INSTALL_CMD}"' in data_js


def test_repository_url_parity() -> None:
    """Canonical repo literal everywhere it appears (entry 44 cells)."""
    data = tomllib.loads(_read("pyproject.toml"))
    urls = data["project"]["urls"]
    for key in ("Homepage", "Source", "Website"):
        assert urls.get(key) == REPO_URL, f"project.urls.{key} = {urls.get(key)!r}"
    assert urls.get("Changelog", "").startswith(REPO_URL + "/")
    assert urls.get("Issues", "").startswith(REPO_URL + "/")

    readme = _read("README.md")
    assert REPO_URL in readme, "README lost the canonical repo URL"
    assert "plamen/django-forge" not in readme, "stale owner in README"

    template_readme = _read("django_forge/templates/README.md.j2")
    assert REPO_URL in template_readme, "template README lost the canonical URL"
    assert "plamen/django-forge" not in template_readme

    data_js = _read_optional("site/src/lib/forge-data.js")
    if data_js is None:
        skipped.append("repository URL: site/src/lib/forge-data.js (artifact absent)")
    elif "github.com" in data_js:
        assert REPO_URL in data_js, "forge-data.js carries a foreign repo URL"
    else:
        skipped.append("repository URL: site/src/lib/forge-data.js (cell absent)")


def test_version_parity() -> None:
    """pyproject, __version__ and forge-data.js agree on the release number."""
    version = _version()
    assert django_forge.__version__ == version, (
        django_forge.__version__,
        version,
    )
    data_js = _read_optional("site/src/lib/forge-data.js")
    if data_js is None:
        skipped.append("version: site/src/lib/forge-data.js (artifact absent)")
    else:
        match = re.search(r'FORGE_VERSION\s*=\s*"([0-9][^"]*)"', data_js)
        assert match, "forge-data.js has no FORGE_VERSION"
        assert match.group(1) == version, (match.group(1), version)

    readme = _read("README.md")
    banner = re.search(r"FORGE v([0-9][0-9.]*)", readme)
    if banner:
        assert banner.group(1) == version, (banner.group(1), version)
    else:
        skipped.append("version: README banner (cell absent)")

    template_readme = _read("django_forge/templates/README.md.j2")
    version_in_template = re.search(r"FORGE v([0-9][0-9.]*)", template_readme)
    if version_in_template:
        assert version_in_template.group(1) == version
    else:
        skipped.append("version: template README banner (cell absent)")


def test_skipped_cells_are_named() -> None:
    """Absent cells were skipped by name (never silently)."""
    # Purely informational: fails only if a skip list item lost its name tag.
    for item in skipped:
        assert ":" in item and "(" in item, item
