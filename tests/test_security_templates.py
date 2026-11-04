"""Adversarial tests for security, logging, and final templates (Story 1.6)."""

import ast
import re
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from django_forge.renderer import Renderer

PROJECT_TEMPLATES = Path(__file__).resolve().parent.parent / "django_forge" / "templates"

BASE_CONTEXT = {
    "project_name": "testproj",
    "project_slug": "testproj",
    "secret_key": "key",
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


@pytest.fixture
def rendered(request: pytest.FixtureRequest) -> Iterator[Path]:
    """Render templates and yield the target directory."""
    ctx = getattr(request, "param", None)
    renderer = Renderer(PROJECT_TEMPLATES)
    c = dict(BASE_CONTEXT)
    if ctx:
        c.update(ctx)
    tmpdir = tempfile.mkdtemp()
    target = Path(tmpdir)
    renderer.render_project(c, target)
    yield target
    shutil.rmtree(target, ignore_errors=True)


# ---------------------------------------------------------------------------
# LOGGING configuration
# ---------------------------------------------------------------------------


def test_logging_config_present(rendered: Path) -> None:
    """1.6.A — base.py has LOGGING dict with console handler."""
    src = (rendered / "config" / "settings" / "base.py").read_text()
    assert "LOGGING" in src
    assert "StreamHandler" in src
    assert '"level": "INFO"' in src or "'level': 'INFO'" in src


def test_logging_has_formatter(rendered: Path) -> None:
    """1.6.K — Logging has a console formatter."""
    src = (rendered / "config" / "settings" / "base.py").read_text()
    assert "formatters" in src
    assert '"format":' in src or "'format':" in src


# ---------------------------------------------------------------------------
# Security settings
# ---------------------------------------------------------------------------


def test_security_settings_present_in_prod(rendered: Path) -> None:
    """1.6.B — Security settings are present in prod.py.

    They live in prod.py, not base.py: base.py is imported with DEBUG=True
    by default, so an ``if not DEBUG:`` block there would evaluate before
    prod.py flips the flag and the settings would never apply.
    """
    src = (rendered / "config" / "settings" / "prod.py").read_text()
    assert "SECURE_SSL_REDIRECT" in src
    assert "SESSION_COOKIE_SECURE" in src
    assert "CSRF_COOKIE_SECURE" in src
    assert "SECURE_HSTS_SECONDS" in src
    assert "SECURE_HSTS_INCLUDE_SUBDOMAINS" in src
    assert "SECURE_PROXY_SSL_HEADER" in src
    assert "SECURE_REFERRER_POLICY" in src
    # 0.4 keeps them enabled, not merely declared (design entry 43).
    assert "SECURE_SSL_REDIRECT = True" in src
    assert "SESSION_COOKIE_SECURE = True" in src
    assert "CSRF_COOKIE_SECURE = True" in src
    assert "SECURE_HSTS_SECONDS = 31536000" in src
    assert "SECURE_HSTS_INCLUDE_SUBDOMAINS = True" in src


def _prod_reexports(prod: str) -> list[str]:
    """Names ``prod.py`` imports explicitly from ``config.settings.base``."""
    names: list[str] = []
    for node in ast.walk(ast.parse(prod)):
        if isinstance(node, ast.ImportFrom) and node.module == "config.settings.base":
            names.extend(alias.name for alias in node.names)
    return names


def _base_definitions(base: str) -> set[str]:
    """Module-level names ``config/settings/base.py`` defines."""
    defined: set[str] = set()
    for node in ast.parse(base).body:
        if isinstance(node, ast.Assign):
            defined.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            defined.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
    return defined


def test_base_prod_parity_guard(rendered: Path) -> None:
    """Decision A: the base/prod security parity guard.

    * ``prod.py`` re-exports explicitly (no ``import *``) and every name it
      imports must still exist in ``base.py`` — drift shows up as an ImportError.
    * the security block lives in ``prod.py`` only, so neither file can quietly
      move or weaken it without this test noticing.
    * both files read ``SECRET_KEY`` / ``ALLOWED_HOSTS`` from the same
      env-driven source (no ``ALLOWED_HOSTS = ["*"]`` anywhere).
    """
    base = (rendered / "config" / "settings" / "base.py").read_text()
    prod = (rendered / "config" / "settings" / "prod.py").read_text()

    assert "from config.settings.base import *" not in prod
    missing = [name for name in _prod_reexports(prod) if name not in _base_definitions(base)]
    assert missing == [], f"prod re-exports names base no longer defines: {missing}"

    security_flags = (
        "SECURE_SSL_REDIRECT",
        "SECURE_PROXY_SSL_HEADER",
        "SESSION_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
        "SECURE_HSTS_SECONDS",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "SECURE_HSTS_PRELOAD",
        "SECURE_CONTENT_TYPE_NOSNIFF",
        "SECURE_REFERRER_POLICY",
        "X_FRAME_OPTIONS",
    )
    for flag in security_flags:
        assert f"{flag} =" in prod, f"prod must enable {flag}"
        assert f"{flag} =" not in base, f"{flag} must not drift into base"

    assert "SECRET_KEY = settings.django_secret_key" in base
    assert not re.search(r"(?m)^SECRET_KEY\s*=", prod), "prod must reuse base's SECRET_KEY"
    assert "ALLOWED_HOSTS = settings.allowed_hosts" in base
    assert "ALLOWED_HOSTS = settings.allowed_hosts" in prod
    assert 'ALLOWED_HOSTS = ["*"]' not in base + prod


def test_security_settings_not_gated_on_import_time_debug(rendered: Path) -> None:
    """Security settings must not be gated on `if not DEBUG` in base.py.

    Regression: the old base.py evaluated `if not DEBUG:` at import time
    (DEBUG defaulted to True), so the block never fired for prod.py which
    sets DEBUG=False only after importing base.
    """
    base = (rendered / "config" / "settings" / "base.py").read_text()
    prod = (rendered / "config" / "settings" / "prod.py").read_text()
    assert "if not DEBUG:" not in base
    assert "if not DEBUG:" not in prod
    assert "SECURE_SSL_REDIRECT" in prod


def test_xss_filter_setting_removed(rendered: Path) -> None:
    """SECURE_BROWSER_XSS_FILTER was removed in Django 5.0 (generated
    projects pin django~=6.1) — it must not appear in any settings file."""
    base = (rendered / "config" / "settings" / "base.py").read_text()
    prod = (rendered / "config" / "settings" / "prod.py").read_text()
    assert "SECURE_BROWSER_XSS_FILTER" not in base
    assert "SECURE_BROWSER_XSS_FILTER" not in prod


# ---------------------------------------------------------------------------
# base.html
# ---------------------------------------------------------------------------


def test_base_html_has_blocks(rendered: Path) -> None:
    """1.6.C — base.html has HTML structure with blocks."""
    src = (rendered / "templates" / "base.html").read_text()
    assert "<!DOCTYPE html>" in src
    assert "{% block content %}" in src
    assert "{% endblock content %}" in src
    assert "{% block title %}" in src


def test_base_html_references_project(rendered: Path) -> None:
    """base.html references project_name in title."""
    src = (rendered / "templates" / "base.html").read_text()
    assert "testproj" in src


# ---------------------------------------------------------------------------
# views.py
# ---------------------------------------------------------------------------


def test_views_has_login_and_profile(rendered: Path) -> None:
    """1.6.D — views.py has LoginView and ProfileView."""
    src = (rendered / "apps" / "accounts" / "views.py").read_text()
    assert "LoginView" in src
    assert "LoginRequiredMixin" in src
    assert "ProfileView" in src
    assert "SignupView" in src


# ---------------------------------------------------------------------------
# api.py — pure Django context
# ---------------------------------------------------------------------------


def test_api_pure_django_stub(rendered: Path) -> None:
    """api.py for pure Django has a comment about adding DRF later."""
    src = (rendered / "apps" / "accounts" / "api.py").read_text()
    assert "No API framework selected" in src


# ---------------------------------------------------------------------------
# api.py — DRF context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rendered",
    [{"use_drf": True, "use_pure_django": False}],
    indirect=True,
)
def test_api_drf_has_viewset(rendered: Path) -> None:
    """1.6.J — api.py for DRF has ModelViewSet."""
    src = (rendered / "apps" / "accounts" / "api.py").read_text()
    assert "ModelViewSet" in src
    assert "UserSerializer" in src
    assert "ReadOnlyModelViewSet" in src


# ---------------------------------------------------------------------------
# api.py — Ninja context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rendered",
    [{"use_ninja": True, "use_drf": False, "use_pure_django": False}],
    indirect=True,
)
def test_api_ninja_has_router(rendered: Path) -> None:
    """api.py for Ninja has Router."""
    src = (rendered / "apps" / "accounts" / "api.py").read_text()
    assert "Router" in src
    assert "list_users" in src


# ---------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------


def test_readme_exists(rendered: Path) -> None:
    """1.6.F — README.md exists with project name."""
    src = (rendered / "README.md").read_text()
    assert "# testproj" in src
    assert "django-forge" in src
    assert "uv sync" in src
    assert "make lint" in src


# ---------------------------------------------------------------------------
# All new templates render without UndefinedError (already covered by
# test_all_templates_render_with_minimal_context but we validate specific files)
# ---------------------------------------------------------------------------


def test_all_story6_templates_exist(rendered: Path) -> None:
    """All Story 1.6 template files exist in rendered output."""
    assert (rendered / "templates" / "base.html").exists()
    assert (rendered / "apps" / "accounts" / "views.py").exists()
    assert (rendered / "apps" / "accounts" / "api.py").exists()
    assert (rendered / "README.md").exists()


# ---------------------------------------------------------------------------
# Secret handling and deployment surfaces (django-forge 0.4, design entry 43)
# ---------------------------------------------------------------------------


def test_no_template_contains_real_secret_key() -> None:
    """No template may carry a real key — or ever render ``secret_key`` (G8).

    The generated key exists only in the gitignored ``.env`` that
    ``forge-django start`` writes; every tracked artifact holds a placeholder.
    """
    pattern = re.compile(r"django-insecure-|\{\{\s*secret_key\s*\}\}")
    leaks: list[str] = []
    for path in sorted(PROJECT_TEMPLATES.rglob("*")):
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:  # pragma: no cover - all templates are text
            continue
        if pattern.search(source):
            leaks.append(path.name)
    assert leaks == [], f"templates carrying a real/leaked secret: {leaks}"


def test_env_example_secret_placeholder_is_exact(rendered: Path) -> None:
    """.env.example carries exactly the ``DJANGO_SECRET_KEY=***`` placeholder."""
    content = (rendered / ".env.example").read_text()
    lines = [line for line in content.splitlines() if line.startswith("DJANGO_SECRET_KEY")]
    assert lines == ["DJANGO_SECRET_KEY=***"]


@pytest.mark.parametrize("rendered", [{"layers": ["docker"], "has_docker": True}], indirect=True)
def test_deployment_surfaces_select_prod_settings(rendered: Path) -> None:
    """compose.yaml and the Dockerfile select config.settings.prod (decision A)."""
    compose = (rendered / "compose.yaml").read_text()
    dockerfile = (rendered / "Dockerfile").read_text()
    assert "DJANGO_SETTINGS_MODULE=config.settings.prod" in compose
    assert "ENV DJANGO_SETTINGS_MODULE=config.settings.prod" in dockerfile
    assert "config.settings.dev" not in compose
    assert "config.settings.dev" not in dockerfile
