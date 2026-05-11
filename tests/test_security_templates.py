"""Adversarial tests for security, logging, and final templates (Story 1.6)."""

import shutil
import tempfile
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
def rendered(request: pytest.FixtureRequest) -> Path:
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


def test_security_settings_present(rendered: Path) -> None:
    """1.6.B — Security settings are present in base.py."""
    src = (rendered / "config" / "settings" / "base.py").read_text()
    assert "SECURE_SSL_REDIRECT" in src
    assert "SESSION_COOKIE_SECURE" in src
    assert "CSRF_COOKIE_SECURE" in src
    assert "SECURE_HSTS_SECONDS" in src
    assert "SECURE_HSTS_INCLUDE_SUBDOMAINS" in src
    assert "SECURE_BROWSER_XSS_FILTER" in src


def test_security_settings_inside_if_not_debug(rendered: Path) -> None:
    """1.6.L — Security settings are wrapped in if not DEBUG condition."""
    src = (rendered / "config" / "settings" / "base.py").read_text()
    assert "not DEBUG" in src
    assert "if not DEBUG:" in src


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
