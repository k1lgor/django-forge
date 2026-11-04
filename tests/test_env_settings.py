"""Acceptance cases (a) and (b) from the Verification Plan (entry 61).

(a) env-only flow: render a project, materialise ``.env`` with the generated
key, import the settings module — the value reaches settings; both
``postgresql://`` and ``postgres://`` yield a postgresql engine; an
unparsable ``DATABASE_URL`` raises instead of falling back.

(b) deploy-check classification: ``DEBUG = True`` and an insecure key fail
the run, proxy warnings pass via the checklist (G4).
"""

import contextlib
import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from django_forge.cli.installer import (
    _is_blocking_issue,
    _parse_check_issues,
    _run_check_deploy,
)
from django_forge.cli.start import _generate_secret_key, _write_env_file
from django_forge.project import build_context
from django_forge.renderer import Renderer

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "django_forge" / "templates"


def _set_env_line(env_file: Path, key: str, value: str) -> None:
    """Replace or append ``key=value`` inside a materialised .env."""
    lines = env_file.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith(key + "="):
            lines[index] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


@contextlib.contextmanager
def _booted_settings(db: str, env_patch: dict[str, str] | None = None):
    """Render + chdir + import ``config.settings.base``; cleans up fully."""
    tmp = Path(tempfile.mkdtemp(prefix="envsettings-"))
    target = tmp / "proj"
    target.mkdir()
    renderer = Renderer(TEMPLATE_ROOT)
    context = build_context({"project_name": "envtest", "api": "drf", "db": db, "layers": []})
    renderer.render_project(context, target, policy="overwrite")
    secret = _generate_secret_key()
    _write_env_file(target, secret)
    env_file = target / ".env"
    for key, value in (env_patch or {}).items():
        _set_env_line(env_file, key, value)

    popped = {
        key: os.environ.pop(key)
        for key in list(os.environ)
        if key in ("DATABASE_URL", "DJANGO_DEBUG", "DJANGO_SECRET_KEY")
    }
    saved_modules = {
        name: sys.modules.pop(name)
        for name in list(sys.modules)
        if name == "config" or name.startswith("config.")
    }
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    sys.path.insert(0, str(target))
    os.chdir(target)
    try:
        module = importlib.import_module("config.settings.base")
        yield module, secret, target
    finally:
        for name in [n for n in sys.modules if n == "config" or n.startswith("config.")]:
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        os.chdir(old_cwd)
        sys.path[:] = old_path
        os.environ.update(popped)
        shutil.rmtree(tmp, ignore_errors=True)


def test_env_only_secret_reaches_settings() -> None:
    """Case (a): only .env carries the key — and settings read it from there."""
    with _booted_settings("sqlite") as (module, secret, target):
        assert module.settings.django_secret_key == secret
        assert secret == module.SECRET_KEY
        assert module.settings.django_debug is True
        # The tracked artifacts never carry the real value.
        assert secret not in (target / ".env.example").read_text(encoding="utf-8")
        assert secret not in (target / "config" / "settings" / "base.py").read_text(
            encoding="utf-8"
        )
        gitignore = (target / ".gitignore").read_text(encoding="utf-8")
        assert any(line.strip() == ".env" for line in gitignore.splitlines())


def test_postgres_default_reaches_engine() -> None:
    """Case (a): the scaffolded postgresql:// DSN configures a pg engine."""
    with _booted_settings("postgres") as (module, _secret, _target):
        default = module.DATABASES["default"]
        assert default["ENGINE"] == "django.db.backends.postgresql"
        assert default.get("NAME"), "database name missing"


@pytest.mark.parametrize("scheme", ["postgresql://", "postgres://"])
def test_both_url_schemes_resolve_to_postgresql(scheme: str) -> None:
    """Case (a): legacy postgres:// and postgresql:// both select pg (G3)."""
    dsn = f"{scheme}envuser:***@localhost:5432/envtest"
    with _booted_settings("postgres", {"DATABASE_URL": dsn}) as (module, _s, _t):
        assert module.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_unparsable_database_url_raises() -> None:
    """Case (a): a broken DATABASE_URL raises a readable error, no fallback."""
    with (
        pytest.raises(ValueError, match="unparsable"),
        _booted_settings("postgres", {"DATABASE_URL": "not a database url"}),
    ):
        pytest.fail("unparsable DATABASE_URL did not raise")  # ty: ignore


def test_unparsable_database_url_error_is_readable() -> None:
    try:
        with _booted_settings("postgres", {"DATABASE_URL": ":::broken:::"}):
            pass
    except ValueError as exc:
        assert "unparsable" in str(exc)
        assert "DATABASE_URL" in str(exc)
    else:  # pragma: no cover - fail loudly if no error
        pytest.fail("expected a ValueError")  # ty: ignore


def test_blocking_classification() -> None:
    """Case (b): DEBUG and insecure keys block; proxy warnings do not (G4)."""
    assert _is_blocking_issue("security.W018") is True  # DEBUG = True
    assert _is_blocking_issue("security.W009") is True  # insecure key
    assert _is_blocking_issue("security.W025") is True  # empty/short key
    assert _is_blocking_issue("security.W008") is False  # proxy-dependent
    assert _is_blocking_issue("security.W042") is False  # other warning
    assert _is_blocking_issue("auth.E001") is True  # check errors block


def test_parse_check_issues_including_hints() -> None:
    """The parser extracts ids, messages and merges HINT lines."""
    output = (
        "System check identified no issues (0 silenced)\n"
        "WARNINGS:\n"
        "security.W008: DEBUG = True\n"
        "HINT: Set DEBUG = False for production.\n"
        "security.W009: The SECRET_KEY setting is not secure.\n"
        "ERRORS:\n"
        "auth.E001: 'auth.User' must define a unique field.\n"
    )
    issues = dict(_parse_check_issues(output))
    assert "security.W008" in issues and "security.W009" in issues
    assert "auth.E001" in issues
    assert "DEBUG = True" in issues["security.W008"]
    assert "HINT" not in issues["security.W008"].upper().replace("HINT", "", 0)
    assert "(Set DEBUG = False for production.)" in issues["security.W008"]


PROXY_OUTPUT = "WARNINGS:\nsecurity.W008: Django does not transmit the SECURITY_PROXY_SSL_HEADER\n"
DEBUG_OUTPUT = "WARNINGS:\nsecurity.W018: The DEBUG setting is True.\n"
INSECURE_KEY_OUTPUT = "WARNINGS:\nsecurity.W009: The SECRET_KEY is insecure.\n"


def test_deploy_check_passes_with_proxy_warnings_only() -> None:
    """Case (b): proxy warnings become a checklist and the run passes."""
    with patch(
        "django_forge.cli.installer._run_cmd",
        return_value=(0, PROXY_OUTPUT, None),
    ) as mocked:
        assert _run_check_deploy(Path("envtest")) is True
        assert mocked.call_args.args[0][-1] == "--settings=config.settings.prod"


@pytest.mark.parametrize("output", [DEBUG_OUTPUT, INSECURE_KEY_OUTPUT])
def test_deploy_check_fails_on_debug_and_insecure_key(output: str) -> None:
    """Case (b): DEBUG=True and an insecure key fail the deploy check."""
    with patch(
        "django_forge.cli.installer._run_cmd",
        return_value=(0, output, None),
    ):
        assert _run_check_deploy(Path("envtest")) is False


def test_deploy_check_fails_on_crash_returncode() -> None:
    """A non-zero check exit (error/crash) fails regardless of parsing."""
    with patch("django_forge.cli.installer._run_cmd", return_value=(1, "", None)):
        assert _run_check_deploy(Path("envtest")) is False
