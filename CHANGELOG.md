# Changelog

All notable changes to django-forge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-11

### Added

- **`forge add <layer>`** — Add optional layers to existing forge projects:
  - `forge add docker` — Dockerfile, compose.yaml, .dockerignore
  - `forge add celery` — Celery worker, tasks, settings, Redis cache deps
  - `forge add email` — Email config, env vars, dev/prod settings
  - Layer validation: unknown layer name shows clear error
  - Non-forge project detection: "Not a forge project. Run 'forge start' first."
  - Already-installed detection: prints "Docker already installed."
  - Overwrite confirmation: lists affected files, prompts before patching
  - Context preservation: existing layers preserved when adding new ones
- **`forge upgrade`** — Re-apply all templates to an existing project:
  - Reads `.forge.toml`, builds full context from existing settings
  - Lists files that will be overwritten, prompts for confirmation
  - Updates `.forge.toml` with the latest version
  - Safe on non-forge projects (shows clear error message)
- **`django-debug-toolbar`** — Always included as a dev-only tool:
  - Added to `dev.py` settings (`INSTALLED_APPS`, `MIDDLEWARE`, `INTERNAL_IPS`)
  - URL route wired in `urls.py` (active only when `DEBUG=True`)
  - Declared as dev dependency in generated `pyproject.toml`

### Fixed

- Package discovery: `MANIFEST.in` added to include dot-file templates in wheel
- Module path matching: all 22 templates use `config.settings.base` prefix
- Build backend: `setuptools.backends._legacy` → `setuptools.build_meta`
- Allauth deprecation: migrated to `ACCOUNT_LOGIN_METHODS` API
- Missing runtime dependency: `tomli` added for `.forge.toml` parsing
- Package discovery: `[tool.setuptools.packages.find]` include rule for flat layout
- Post-install flow: added `makemigrations accounts` step before `migrate`
- Upgrade regression: `.forge.toml` excluded from overwrite confirmation prompt

## [0.1.0] — 2026-05-11

### Added

- **`forge start <project-name>`** — Interactive scaffold with 3 questions:
  - API framework: DRF, Django-Ninja, or Pure Django
  - Database: PostgreSQL (production) + SQLite (development), or SQLite only
  - Optional layers: Docker, Celery, Email (multi-select)
- **Pure Django scaffold** — Complete production-ready project with:
  - Custom User model with email-based authentication
  - django-allauth integration (session auth)
  - WhiteNoise static files, CORS headers, pydantic-settings
  - Structured logging, Sentry integration (DSN-gated)
  - ASGI via uvicorn, async views, async ORM support
- **DRF scaffold** — Django REST Framework with:
  - JWT auth (djangorestframework-simplejwt)
  - ModelViewSet, serializer, browsable API at `/api/`
- **Django-Ninja scaffold** — Modern API framework with:
  - JWT auth (django-ninja-jwt)
  - Controller, schemas, OpenAPI docs at `/api/docs`
- **PostgreSQL support** — Production-ready database config with:
  - `DATABASE_URL` env var, `psycopg` dependency
  - SQLite in development, PostgreSQL in production
- **Docker optional layer** — Multi-stage Dockerfile + Docker Compose:
  - Build stage (uv sync), production stage (slim image)
  - PostgreSQL or SQLite service based on database choice
- **Celery optional layer** — Background task queue with:
  - Redis broker, auto-discover tasks, sample `add` task
  - Django cache backend (Redis) when Celery selected
- **Email optional layer** — Mailpit (dev) / SMTP (prod) configuration:
  - Console backend in development, SMTP in production
  - Docker Compose Mailpit service when Email + Docker selected
- **Project tooling** — Every scaffold includes:
  - ruff (linter + formatter), ty (type checker, by Astral)
  - pytest, pytest-django, coverage, factory_boy
  - GitHub Actions CI/CD (lint, type-check, test, deploy-check)
  - .pre-commit-config.yaml, Makefile
- **`forge list`** — Discover available frameworks, optional layers, and core layers
- **`--no-input` mode** — Skip interactive prompts for CI/CD automation:
  - Defaults: DRF, PostgreSQL+SQLite, no layers
  - Auto-detected via `CI=true` or `GITHUB_ACTIONS=true` env vars
  - CI-proper message ("CI mode detected") when auto-activated

### Security

- Custom User model with email login (no username requirement)
- Production security settings: HSTS, SSL redirect, secure cookies, content sniffing protection
- All installed apps include CORS headers and security middleware
- Secret key generated with `secrets.token_urlsafe(50)` — 66+ chars, Jinja2-safe
- Sentry DSN placeholder (disabled until configured)

### Fixed

- `forge list` ASCII-compatibility on legacy Windows terminals (cp1251)
- CI auto-detection message correctly shows "CI mode detected" instead of "--no-input mode"

### Changed

- Upgraded type checker from `mypy` to `ty` (Astral) — faster, ecosystem-native with `uv` + `ruff`

[0.1.0]: https://github.com/your-org/django-forge/releases/tag/v0.1.0
