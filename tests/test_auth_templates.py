"""Adversarial tests for auth and admin templates (Story 1.5)."""

import importlib.util
import shutil
import sys
import tempfile
import warnings
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

# The three framework cells (design entry 39): every route assertion below is
# pinned per cell against the rendered root URLconf.
PURE_CONTEXT = dict(BASE_CONTEXT)
DRF_CONTEXT = {
    **BASE_CONTEXT,
    "api": "drf",
    "use_drf": True,
    "use_ninja": False,
    "use_pure_django": False,
}
NINJA_CONTEXT = {
    **BASE_CONTEXT,
    "api": "ninja",
    "use_drf": False,
    "use_ninja": True,
    "use_pure_django": False,
}
ALL_MODES = [
    pytest.param("pure", PURE_CONTEXT, id="pure"),
    pytest.param("drf", DRF_CONTEXT, id="drf"),
    pytest.param("ninja", NINJA_CONTEXT, id="ninja"),
]


@pytest.fixture
def rendered(request: pytest.FixtureRequest) -> Iterator[Path]:
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
    # Annotation-agnostic: models.py.j2 carries `REQUIRED_FIELDS: ClassVar[...] = []`.
    assert "REQUIRED_FIELDS" in src and "= []" in src


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


@pytest.mark.parametrize("rendered", [DRF_CONTEXT], indirect=True)
def test_drf_router_lives_in_api_module(rendered: Path) -> None:
    """DRF cell: the DefaultRouter lives in api.py, not in the auth URLs.

    0.4 moved every API route stub out of ``apps/accounts/urls.py`` (file 19):
    that file now carries the auth routes in all three modes, while
    ``api.py`` exposes ``api_urls`` for ``config/urls.py`` to mount.
    """
    urls_src = (rendered / "apps" / "accounts" / "urls.py").read_text()
    assert "DefaultRouter" not in urls_src
    assert "login/" in urls_src

    api_src = (rendered / "apps" / "accounts" / "api.py").read_text()
    assert "DefaultRouter" in api_src
    assert 'router.register(r"users", UserViewSet)' in api_src
    assert "api_urls = include(router.urls)" in api_src


# ---------------------------------------------------------------------------
# URL patterns — Ninja context
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rendered", [NINJA_CONTEXT], indirect=True)
def test_ninja_routes_live_in_api_module(rendered: Path) -> None:
    """Ninja cell: urls.py keeps the auth routes (never an empty urlpatterns).

    Replaces the old ``test_ninja_urls_empty``, which pinned the broken state.
    """
    urls_src = (rendered / "apps" / "accounts" / "urls.py").read_text()
    assert "urlpatterns = []" not in urls_src
    assert "login/" in urls_src
    assert "signup/" in urls_src
    assert "Router" not in urls_src

    api_src = (rendered / "apps" / "accounts" / "api.py").read_text()
    assert "Router" in api_src
    assert "api_urls = include(api.urls[:2]" in api_src


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
# Route resolution against the rendered root URLconf (design entry 39)
# ---------------------------------------------------------------------------


def _require_stack(mode: str) -> None:
    """The generated stack must be importable — otherwise skip, never fail."""
    pytest.importorskip("django", reason="Django is not installed")
    pytest.importorskip("allauth", reason="django-allauth is not installed")
    if mode == "drf":
        pytest.importorskip("rest_framework", reason="djangorestframework is not installed")
    elif mode == "ninja":
        pytest.importorskip("ninja", reason="django-ninja is not installed")


def _configure_django(target: Path) -> None:
    """Configure the minimal Django needed to import the rendered URLconf."""
    import django
    from django.conf import settings

    # ``apps.accounts`` is an installed app, so the rendered tree must be
    # importable *before* the app registry is populated.
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="test",
            ROOT_URLCONF="config.urls",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "django.contrib.admin",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.sites",
                "allauth",
                "allauth.account",
                "allauth.socialaccount",
                "apps.accounts",
            ],
            AUTH_USER_MODEL="accounts.User",
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            MIDDLEWARE=["allauth.account.middleware.AccountMiddleware"],
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ]
                    },
                }
            ],
            SITE_ID=1,
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            USE_TZ=True,
            STATIC_URL="/static/",
            MEDIA_URL="/media/",
        )
    django.setup()
    from django.apps import apps

    if not apps.is_installed("apps.accounts"):
        pytest.skip("Django is already configured without apps.accounts")  # ty: ignore


def _resolve(target: Path, url: str, mode: str):
    """Resolve *url* against the rendered ``config/urls.py`` (``None`` = 404)."""
    _require_stack(mode)
    _configure_django(target)
    # Each render is a fresh tree — drop the previously imported generated
    # packages so the current one is imported from *target*.
    for name in list(sys.modules):
        if name in ("apps", "config") or name.startswith(("apps.", "config.")):
            del sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        "rendered_root_urls", target / "config" / "urls.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        pytest.fail("cannot load the rendered config/urls.py")  # ty: ignore
    module = importlib.util.module_from_spec(spec)
    sys.modules["rendered_root_urls"] = module
    # Every render re-imports the (byte-identical) accounts models, so Django
    # warns about the duplicate registration — that is expected in-process.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Model .* was already registered")
        spec.loader.exec_module(module)

    from django.urls import Resolver404, resolve

    try:
        return resolve(url, urlconf=module)
    except Resolver404:
        return None


def _view_class(match):
    """The view class a resolved route dispatches to (``None`` if a function view)."""
    func = match.func
    return getattr(func, "view_class", None) or getattr(func, "cls", None)


@pytest.mark.parametrize("mode, rendered", ALL_MODES, indirect=["rendered"])
def test_login_resolves_to_custom_view(mode: str, rendered: Path) -> None:
    """``/accounts/login/`` hits the custom view — never allauth's — in every mode.

    Pins the generated ``config/urls.py`` include order: the accounts URLs are
    mounted before ``allauth.urls``, so the custom view wins the match.
    """
    match = _resolve(rendered, "/accounts/login/", mode)
    assert match is not None, "/accounts/login/ must resolve"
    from allauth.account.views import LoginView as AllauthLoginView
    from django.contrib.auth.views import LoginView

    assert _view_class(match) is LoginView
    assert _view_class(match) is not AllauthLoginView


@pytest.mark.parametrize("mode, rendered", ALL_MODES, indirect=["rendered"])
def test_signup_resolves_to_custom_view(mode: str, rendered: Path) -> None:
    """``/accounts/signup/`` maps to the generated SignupView in every mode."""
    match = _resolve(rendered, "/accounts/signup/", mode)
    assert match is not None, "/accounts/signup/ must resolve"
    from apps.accounts.views import SignupView  # ty: ignore[unresolved-import]

    assert _view_class(match) is SignupView


@pytest.mark.parametrize("rendered", [DRF_CONTEXT], indirect=True)
def test_drf_api_users_route_resolves(rendered: Path) -> None:
    """DRF cell: ``resolve('/api/users/')`` — DefaultRouter's trailing slash."""
    match = _resolve(rendered, "/api/users/", "drf")
    assert match is not None, "/api/users/ must resolve (DefaultRouter)"
    from apps.accounts.api import UserViewSet  # ty: ignore[unresolved-import]

    assert _view_class(match) is UserViewSet
    assert _resolve(rendered, "/api/users", "drf") is None, "no-slash is a 404"


@pytest.mark.parametrize("rendered", [NINJA_CONTEXT], indirect=True)
def test_ninja_api_users_route_resolves(rendered: Path) -> None:
    """Ninja cell: ``resolve('/api/users')`` — the router has no trailing slash."""
    match = _resolve(rendered, "/api/users", "ninja")
    assert match is not None, "/api/users must resolve (ninja router)"
    assert match.url_name == "list_users"
    assert str(match.func.__module__).startswith("ninja.")
    assert _resolve(rendered, "/api/users/", "ninja") is None, "slash variant is a 404"


def test_pure_mode_mounts_no_api(rendered: Path) -> None:
    """Pure cell: neither API cell is mounted — no /api/ routes at all."""
    assert _resolve(rendered, "/api/users/", "pure") is None
    assert _resolve(rendered, "/api/users", "pure") is None


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
