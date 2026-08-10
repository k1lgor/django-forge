// Single source of truth for the forge landing page.
// Every artifact path below is a real file the CLI's templates generate.
// Verified against django_forge/templates/*.j2.

export const FORGE_VERSION = "0.2.1";

export const FRAMEWORKS = [
  {
    id: "drf",
    name: "DRF",
    blurb: "Django REST Framework — battle-tested, large ecosystem",
    files: [
      { path: "apps/accounts/api.py", lines: ["class UserSerializer(serializers.ModelSerializer):"] },
    ],
    deps: ["djangorestframework~=3.15.0", "djangorestframework-simplejwt~=5.5.0"],
  },
  {
    id: "ninja",
    name: "Django-Ninja",
    blurb: "Modern, type-hint native, ~5x faster",
    files: [
      { path: "apps/accounts/api.py", lines: ["router = Router()", '@router.get("/users", response=list[UserSchema])'] },
    ],
    deps: ["django-ninja~=1.4.0", "django-ninja-jwt~=5.0.0"],
  },
  {
    id: "pure",
    name: "Pure Django",
    blurb: "Templates + views, no API framework",
    files: [
      { path: "apps/accounts/urls.py", lines: ['path("login/", auth_views.LoginView.as_view(...), name="login")'] },
    ],
    deps: [],
  },
];

export const DATABASES = [
  {
    id: "postgres",
    name: "PostgreSQL + SQLite",
    blurb: "Postgres in production, SQLite for fast local dev",
  },
  {
    id: "sqlite",
    name: "SQLite only",
    blurb: "Simpler setup, no PostgreSQL dependency",
  },
];

export const LAYERS = [
  {
    id: "docker",
    name: "Docker",
    tagline: "Multi-stage build + Compose, gunicorn wired up",
    files: [
      { path: "Dockerfile", lines: ["FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder", 'CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]'] },
      { path: "compose.yaml", lines: ["services:", "  app:", '    build: .'] },
      { path: ".dockerignore", lines: ["__pycache__/", ".venv/", ".env"] },
    ],
    dep: "gunicorn~=23.0",
  },
  {
    id: "celery",
    name: "Celery",
    tagline: "Background task queue with a Redis broker",
    files: [
      { path: "config/celery.py", lines: ['app = Celery("{{ project_slug }}")', 'app.config_from_object("django.conf:settings", namespace="CELERY")'] },
      { path: "apps/accounts/tasks.py", lines: ["@shared_task", "def add(x: int, y: int) -> int:"] },
    ],
    dep: "celery~=5.4.0, redis>=5.0",
  },
  {
    id: "email",
    name: "Email",
    tagline: "Mailpit in dev, SMTP in production",
    files: [
      { path: "config/settings/dev.py", lines: ['EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"'] },
      { path: "config/settings/prod.py", lines: ['EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"'] },
    ],
    dep: "—",
  },
  {
    id: "cache",
    name: "Caching",
    tagline: "Redis cache backend, zero-config location",
    files: [
      { path: "config/settings/base.py", lines: ['"BACKEND": "django.core.cache.backends.redis.RedisCache"'] },
    ],
    dep: "redis>=5.0",
  },
  {
    id: "social",
    name: "Social Auth",
    tagline: "Google + GitHub OAuth via allauth",
    files: [
      { path: "config/settings/base.py", lines: ['SOCIALACCOUNT_PROVIDERS = {"google": {...}, "github": {...}}'] },
    ],
    dep: "—",
  },
  {
    id: "storage",
    name: "S3 Storage",
    tagline: "Static + media on S3/MinIO via django-storages",
    files: [
      { path: "config/settings/base.py", lines: ['"BACKEND": "storages.backends.s3.S3Storage"'] },
    ],
    dep: "django-storages[s3]",
  },
  {
    id: "healthcheck",
    name: "Health Check",
    tagline: "/healthz for load balancers — DB, cache, broker",
    files: [
      { path: "config/urls.py", lines: ['path("healthz/", include("health_check.urls"))'] },
    ],
    dep: "django-health-check~=3.18",
  },
  {
    id: "audit",
    name: "Audit Trail",
    tagline: "Every model change recorded with user + timestamp",
    files: [
      { path: "apps/accounts/models.py", lines: ["history = HistoricalRecords()"] },
      { path: "apps/accounts/admin.py", lines: ["class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):"] },
    ],
    dep: "django-simple-history",
  },
  {
    id: "backup",
    name: "Backup",
    tagline: "Nightly DB dumps + a restore drill",
    files: [
      { path: "config/settings/base.py", lines: ['DBBACKUP_STORAGE = STORAGES["default"]["BACKEND"]'] },
      { path: "Makefile", lines: ["backup:", "\tuv run manage.py dbbackup"] },
    ],
    dep: "django-dbbackup",
  },
  {
    id: "seed",
    name: "Seed Data",
    tagline: "Factory-based dev data in one command",
    files: [
      { path: "apps/accounts/factories.py", lines: ["class UserFactory(factory.django.DjangoModelFactory):"] },
      { path: "apps/accounts/management/commands/seed.py", lines: ["UserFactory()", 'self.stdout.write(self.style.SUCCESS("Created sample users"))'] },
    ],
    dep: "factory-boy (dev)",
  },
  {
    id: "preflight",
    name: "Preflight",
    tagline: "One command: deploy check before you push",
    files: [
      { path: "apps/accounts/management/commands/preflight.py", lines: ['call_command("check", deploy=True)', 'call_command("migrate", check=True)'] },
    ],
    dep: "—",
  },
];

// Files every project gets, in forge order.
export const CORE_FILES = [
  { path: "manage.py", lines: ['os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")'] },
  { path: "pyproject.toml", lines: ["dependencies = [", '    "django~=5.1.0",'] },
  { path: "config/__init__.py", lines: ["# config package"] },
  { path: "config/settings/base.py", lines: ["SECRET_KEY = settings.django_secret_key", 'AUTH_USER_MODEL = "accounts.User"', 'ACCOUNT_LOGIN_METHODS = {"email"}'] },
  { path: "config/settings/dev.py", lines: ["DEBUG = True"] },
  { path: "config/settings/prod.py", lines: ["DEBUG = False", "SECURE_SSL_REDIRECT = True"] },
  { path: "config/urls.py", lines: ['path("admin/", admin.site.urls)', 'path("accounts/", include("allauth.urls"))'] },
  { path: "config/wsgi.py", lines: ["application = get_wsgi_application()"] },
  { path: "config/asgi.py", lines: ["application = get_asgi_application()"] },
  { path: "apps/accounts/models.py", lines: ["class User(AbstractUser):", 'USERNAME_FIELD = "email"'] },
  { path: "apps/accounts/managers.py", lines: ["class UserManager(BaseUserManager):"] },
  { path: "apps/accounts/admin.py", lines: ["@admin.register(User)"] },
  { path: "apps/accounts/forms.py", lines: ["class UserCreationForm(BaseUserCreationForm):"] },
  { path: "apps/accounts/views.py", lines: ["class UserLoginView(LoginView):"] },
  { path: "apps/accounts/signals.py", lines: ["@receiver(post_save, sender=User)"] },
  { path: "apps/accounts/tests/test_models.py", lines: ["def test_create_user_with_email():"] },
  { path: "templates/base.html", lines: ["<title>", "{% block content %}"] },
  { path: "tests/conftest.py", lines: ['os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")'] },
  { path: "tests/test_example.py", lines: ["def test_settings_importable():"] },
  { path: ".env.example", lines: ["DJANGO_SECRET_KEY=", "DJANGO_DEBUG=true"] },
  { path: ".gitignore", lines: ["__pycache__/", ".env", "!.env.example"] },
  { path: "Makefile", lines: [".PHONY: lint typecheck test"] },
  { path: "README.md", lines: ["# {{ project_name }}"] },
  { path: ".forge.toml", lines: ["[forge]", 'version = "0.2.1"'] },
];

// Build the ordered file set for a chosen configuration.
export function buildFileSet({ framework, database, layers }) {
  const fw = FRAMEWORKS.find((f) => f.id === framework) ?? FRAMEWORKS[0];
  const files = CORE_FILES.map((f) => ({ ...f, source: "core" }));

  for (const f of fw.files) files.push({ ...f, source: fw.name });
  for (const id of layers) {
    const layer = LAYERS.find((l) => l.id === id);
    if (layer) {
      for (const f of layer.files) files.push({ ...f, source: layer.name });
    }
  }
  return files;
}

export const SECURITY_CHECKS = [
  {
    claim: "SECRET_KEY comes from the environment",
    detail: "pydantic-settings reads DJANGO_SECRET_KEY from .env; the scaffold never hardcodes a key into code.",
  },
  {
    claim: "Production security is real, not decorative",
    detail: "prod.py sets DEBUG=False, SECURE_SSL_REDIRECT, secure cookies, HSTS and a strict referrer policy — after the import-order bug that once swallowed them was fixed.",
  },
  {
    claim: "Your .env can't be committed",
    detail: "The generated .gitignore ignores .env and .env.* while keeping .env.example tracked.",
  },
  {
    claim: "Hosts are env-driven",
    detail: "ALLOWED_HOSTS is read from the environment — no hardcoded ['*'] in production settings.",
  },
  {
    claim: "Deployment is checked before you finish scaffolding",
    detail: "The wizard runs `manage.py check --deploy` and surfaces warnings before printing the success banner.",
  },
  {
    claim: "Custom User model from the start",
    detail: "AUTH_USER_MODEL = accounts.User with email-based auth — no painful migration to a custom user later.",
  },
];

export const UPGRADE_STATES = [
  {
    file: "config/settings/base.py",
    state: "pristine",
    outcome: "upgraded",
    note: "You never touched it — forge re-renders it with the newest template.",
  },
  {
    file: "apps/accounts/models.py",
    state: "modified",
    outcome: "skipped",
    note: "You added a field — the manifest hash no longer matches, so forge leaves it byte-identical.",
  },
  {
    file: "Makefile",
    state: "pristine",
    outcome: "upgraded",
    note: "Hash matches — refreshed with the latest targets.",
  },
];

export const BOOT_LINES = [
  { kind: "banner", text: "=== FORGE v0.2.1 - django project scaffolder ===", color: "cyan" },
  { kind: "tagline", text: "Ask 3 questions. Get a production-ready Django project.", color: "yellow" },
  { kind: "led", label: "python tooling", ok: "uv · ruff · ty" },
  { kind: "led", label: "auth", ok: "custom user · allauth" },
  { kind: "led", label: "database", ok: "postgres · sqlite" },
  { kind: "led", label: "async", ok: "asgi · uvicorn" },
  { kind: "led", label: "docker", ok: "multi-stage build" },
  { kind: "led", label: "celery", ok: "background tasks" },
  { kind: "led", label: "email", ok: "mailpit · smtp" },
  { kind: "led", label: "cache", ok: "redis backend" },
  { kind: "led", label: "social", ok: "google · github" },
  { kind: "led", label: "storage", ok: "s3 · minio" },
  { kind: "led", label: "healthcheck", ok: "/healthz" },
  { kind: "led", label: "audit", ok: "history on writes" },
  { kind: "led", label: "backup", ok: "nightly dumps" },
  { kind: "led", label: "seed · preflight", ok: "dev data · deploy check" },
  { kind: "prompt", text: "PRESS START", color: "yellow" },
];

export const INSTALL_CMD = "uv tool install django-forge";
export const RUN_CMD = "forge start myproject";
