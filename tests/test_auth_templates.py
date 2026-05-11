"""Adversarial tests for auth and admin templates (Story 1.5)."""

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
    """Render templates with optional custom context via ``request.param``."""
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
# User model
# ---------------------------------------------------------------------------


def test_user_model_username_optional(rendered: Path) -> None:
    """User model has username with blank=True, null=True."""
    src = (rendered / "apps" / "accounts" / "models.py").read_text()
    assert "blank=True" in src
    assert "null=True" in src


def test_user_model_email_unique(rendered: Path) -> None:
    """User model email field has unique=True."""
    src = (rendered / "apps" / "accounts" / "models.py").read_text()
    assert "unique=True" in src
    assert 'USERNAME_FIELD = "email"' in src


def test_user_model_required_fields_empty(rendered: Path) -> None:
    """User model has REQUIRED_FIELDS = []."""
    src = (rendered / "apps" / "accounts" / "models.py").read_text()
    assert "REQUIRED_FIELDS = []" in src


# ---------------------------------------------------------------------------
# Manager edge cases
# ---------------------------------------------------------------------------


def test_manager_password_optional(rendered: Path) -> None:
    """UserManager.create_user accepts password=None."""
    src = (rendered / "apps" / "accounts" / "managers.py").read_text()
    assert "password: str | None = None" in src


def test_manager_superuser_sets_staff(rendered: Path) -> None:
    """create_superuser sets is_staff and is_superuser."""
    src = (rendered / "apps" / "accounts" / "managers.py").read_text()
    assert 'extra_fields.setdefault("is_staff", True)' in src
    assert 'extra_fields.setdefault("is_superuser", True)' in src


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


def test_admin_list_display(rendered: Path) -> None:
    """UserAdmin has list_display with email."""
    src = (rendered / "apps" / "accounts" / "admin.py").read_text()
    assert "list_display" in src
    assert "is_active" in src


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


def test_signals_get_user_model(rendered: Path) -> None:
    """Signals uses get_user_model()."""
    src = (rendered / "apps" / "accounts" / "signals.py").read_text()
    assert "get_user_model" in src


def test_signals_post_save(rendered: Path) -> None:
    """Signals has post_save receiver."""
    src = (rendered / "apps" / "accounts" / "signals.py").read_text()
    assert "post_save" in src
    assert "@receiver" in src


# ---------------------------------------------------------------------------
# URL patterns — DRF context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rendered",
    [{"use_drf": True, "use_pure_django": False}],
    indirect=True,
)
def test_drf_urls_router(rendered: Path) -> None:
    """DRF context URLs use DefaultRouter."""
    src = (rendered / "apps" / "accounts" / "urls.py").read_text()
    assert "DefaultRouter" in src


# ---------------------------------------------------------------------------
# URL patterns — pure Django context
# ---------------------------------------------------------------------------


def test_pure_django_urls_views(rendered: Path) -> None:
    """Pure Django URLs have login/logout/password-reset paths."""
    src = (rendered / "apps" / "accounts" / "urls.py").read_text()
    assert "login/" in src
    assert "logout/" in src
    assert "password-reset/" in src


# ---------------------------------------------------------------------------
# URL patterns — Ninja context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rendered",
    [{"use_ninja": True, "use_drf": False, "use_pure_django": False}],
    indirect=True,
)
def test_ninja_urls_empty(rendered: Path) -> None:
    """Ninja context URLs are empty (routing in main api.py)."""
    src = (rendered / "apps" / "accounts" / "urls.py").read_text()
    assert "urlpatterns = []" in src


# ---------------------------------------------------------------------------
# Apps.py ready method
# ---------------------------------------------------------------------------


def test_apps_ready_signals(rendered: Path) -> None:
    """apps.py ready() imports signals."""
    src = (rendered / "apps" / "accounts" / "apps.py").read_text()
    assert "ready" in src
    assert "signals" in src


# ---------------------------------------------------------------------------
# Test file
# ---------------------------------------------------------------------------


def test_test_models_has_scenarios(rendered: Path) -> None:
    """test_models.py has user creation test scenarios."""
    src = (rendered / "apps" / "accounts" / "tests" / "test_models.py").read_text()
    assert "create_user" in src
    assert "create_superuser" in src


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------


def test_forms_has_creation_form(rendered: Path) -> None:
    """Forms have UserCreationForm."""
    src = (rendered / "apps" / "accounts" / "forms.py").read_text()
    assert "UserCreationForm" in src


# ---------------------------------------------------------------------------
# All auth templates with DRF + PostgreSQL context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rendered",
    [{"use_drf": True, "api": "drf", "db": "postgres", "use_pure_django": False}],
    indirect=True,
)
def test_auth_templates_drf_postgres(rendered: Path) -> None:
    """Auth templates render with DRF + PostgreSQL without error."""
    assert (rendered / "apps" / "accounts" / "models.py").exists()
    assert (rendered / "apps" / "accounts" / "urls.py").exists()
    assert (rendered / "apps" / "accounts" / "admin.py").exists()
