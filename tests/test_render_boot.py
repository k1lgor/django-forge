"""Render-to-boot regression: every generated .py compiles, no comment glue.

Design entry 45 — full `manage.py check` runs in the CI e2e job (file 47);
this is the unit-level twin: byte-compile the render matrix, assert the
comment-glue artifact class (# Databasedatabase_url, # SecurityDATABASE_URL)
never survives, and assert `database_url` is defined for db=postgres.
"""

import re
from pathlib import Path

import pytest

from django_forge.project import build_context
from django_forge.renderer import Renderer

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "django_forge" / "templates"

# A comment marker immediately followed by a non-space token (no space after #).
_INLINE_GLUE = re.compile(r"#(?![ \t\n])")
# A capitalized comment word whose NEXT character is alphanumeric means the
# following statement got glued onto the comment (the B2 class: a regex that
# backtracks across the word boundary false-positives on normal prose, so the
# boundary is checked positionally after the greedy word match instead).
_COMMENT_WORD = re.compile(r"(?:^|\s)#\s+([A-Z][a-z]+)")
_AFTER_WORD = re.compile(r"[A-Za-z0-9_]")


def _has_runon(line: str) -> bool:
    """True when a comment word runs straight into an env-var/flag token.

    CamelCase words (``# NoDecode``) are legitimate; the B2 glue class always
    continues with ``_`` or an uppercase run (``# SecurityDATABASE_URL``,
    ``# Databasedatabase_url``), so the marker after the greedy first word
    decides.
    """
    if line.lstrip().startswith("#!"):
        return False
    for match in _COMMENT_WORD.finditer(line):
        end = match.end()
        if end >= len(line):
            continue
        if line[end] == "_":
            return True
        if line[end].isupper() and end + 1 < len(line) and line[end + 1].isupper():
            return True
    return False


COMBOS = [(api, db) for api in ("drf", "ninja", "pure") for db in ("postgres", "sqlite")]


def _render(tmp_path: Path, api: str, db: str) -> Path:
    target = tmp_path / f"{api}_{db}"
    renderer = Renderer(TEMPLATE_ROOT)
    context = build_context(
        {"project_name": "boottest", "api": api, "db": db, "layers": ["celery"]}
    )
    renderer.render_project(context, target, policy="overwrite")
    return target


@pytest.mark.parametrize(("api", "db"), COMBOS)
def test_generated_python_byte_compiles(tmp_path: Path, api: str, db: str) -> None:
    """Every rendered .py compiles (syntax level) in this combo."""
    target = _render(tmp_path, api, db)
    py_files = sorted(target.rglob("*.py"))
    assert py_files, "render produced no python files"
    for path in py_files:
        source = path.read_text(encoding="utf-8")
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:  # pragma: no cover - fails loudly
            raise AssertionError(f"{path.relative_to(target)}: {exc}") from exc


@pytest.mark.parametrize(("api", "db"), COMBOS)
def test_no_comment_glue_artifacts(tmp_path: Path, api: str, db: str) -> None:
    """No comment marker runs into a token (the B2 glue class)."""
    target = _render(tmp_path, api, db)
    for path in sorted(target.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.lstrip().startswith("#!"):
                continue  # shebang
            if _INLINE_GLUE.search(line):
                raise AssertionError(
                    f"{path.relative_to(target)}:{lineno}: # glued to a token: {line.strip()}"
                )
            if _has_runon(line):
                raise AssertionError(
                    f"{path.relative_to(target)}:{lineno}: comment run-on: {line.strip()}"
                )


@pytest.mark.parametrize("db", ["postgres", "sqlite"])
def test_database_url_field_defined(tmp_path: Path, db: str) -> None:
    """The settings module exposes `database_url` for both db cells."""
    target = _render(tmp_path, "drf", db)
    base = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert re.search(r"(?m)^\s*database_url\s*:", base), f"no database_url field (db={db})"


def test_postgres_default_dsn_uses_postgresql_scheme(tmp_path: Path) -> None:
    """postgres cells default to a postgresql:// DSN (Decision 4 wiring)."""
    target = _render(tmp_path, "drf", "postgres")
    base = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert 'database_url: str = "postgresql://' in base
    env_example = (target / ".env.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=postgresql://" in env_example
