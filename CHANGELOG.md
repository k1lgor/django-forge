# Changelog

All notable changes to django-forge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Landing page (`site/`)** — A Svelte 5 + Vite single-page site for django-forge:
  - Terminal boot sequence hero (typewriter + 11-layer power-on self-test, once per session)
  - Interactive forge simulator — answer the 3 wizard questions and watch a real
    project tree forge itself, built entirely from embedded data (zero network requests)
  - Eleven layer cards (open as a zoom-in modal showing the real generated files)
  - "Production-ready by default" security checklist and "your edits survive"
    upgrade-path panel, both grounded in the actual generated templates
  - No-JS fallback, `prefers-reduced-motion` support; ~23 kB gzip JS, no images/fonts
  - **GitHub Pages workflow** — deploys on pushes that touch `site/**` only
- **Health Check optional layer** — django-health-check at `/healthz/` (DB check
  always; cache/broker checks when those layers exist). `forge start` (option 7)
  and `forge add healthcheck`.
- **Audit Trail optional layer** — django-simple-history on the custom User
  (`HistoricalRecords`, history middleware, `SimpleHistoryAdmin`). Option 8 /
  `forge add audit` (prints the migration next-steps).
- **Backup optional layer** — django-dbbackup nightly dumps (S3 when the storage
  layer is present, else `backups/`), `make backup` / `make restore`. Option 9 /
  `forge add backup`.
- **Seed Data optional layer** — factory-boy `UserFactory` + `manage.py seed`,
  `make seed`. Option 10 / `forge add seed`.
- **Preflight optional layer** — `manage.py preflight` (deploy check, pending
  migrations, `migrate --check`) with clean failure on errors. Option 11 /
  `forge add preflight`.

### Fixed

- **User edits survive `forge add` / `forge upgrade`** — the renderer now writes a
  `.forge-manifest.json` (per-file sha256) and re-renders with a pristine policy:
  forge-owned files are refreshed, user-modified files are skipped byte-for-byte.
- **`SECRET_KEY` no longer blanked on re-render** — add/upgrade read the existing
  key back from `.env` or `base.py` instead of writing an empty one.
- **`forge start --no-input` no longer deletes existing directories** — it refuses
  with a message instead of silently `rmtree`-ing.
- **Project names are validated** — path separators, `..`, leading dots and Jinja
  delimiters are rejected before anything touches disk.
- **Production security settings actually apply** — secure-cookie/HSTS/SSL-redirect
  settings moved out of base's import-time `if not DEBUG:` block into `prod.py`;
  `ALLOWED_HOSTS` is env-driven; removed `SECURE_BROWSER_XSS_FILTER` (gone in
  Django 5.0).
- **Generated projects install and boot** — `urls.py` no longer imports
  `debug_toolbar` unconditionally (dev extra), the Docker image's gunicorn is
  declared as a dependency, and `.env` is gitignored while `.env.example` stays
  tracked.
- **`forge add backup` uses a real S3 backend** — django-dbbackup 4.x removed its
  bundled S3 storage; backups now reuse the storage layer's configured backend.
- **`forge` no longer crashes on Windows when output is piped** — rich renders with
  ANSI instead of the Win32 console API.
- **`forge upgrade` preserves unknown keys** — `.forge.toml` extra sections and
  keys survive a layers update.

### Changed

- Renderer writes files atomically and refuses symlink escapes outside the project.
- `preflight` fails cleanly on check errors instead of raising a traceback.
- Generated `.gitignore` ignores `backups/`; seed docs note the dev extras.

## [0.2.1] — 2026-06-10

### Added

- **User preference cache** — Scaffold choices (api, db, layers) are saved to
  `~/.config/forge/prefs.json` and reloaded as defaults on the next `forge start`.
  All platforms use the same path. Overridable via `FORGE_PREFS_DIR` env var.
- **`createsuperuser` post-scaffold prompt** — After `uv sync` + `migrate` succeed,
  offers to create a Django superuser account interactively. Skips automatically
  in non-TTY environments (CI, piped input, `--no-input`).
- **Caching (Redis) optional layer** — New layer adds Redis cache backend
  (`django.core.cache.backends.redis.RedisCache`). Available via `forge start`
  (option 4) and `forge add cache`. Adds Redis service to Docker Compose
  when Docker is also selected.
- **Social Auth optional layer** — New layer pre-configures Google and GitHub
  OAuth via django-allauth. Adds `SOCIALACCOUNT_PROVIDERS` settings and provider
  environment variables. Available via `forge start` (option 5) and
  `forge add social`.
- **S3 Storage optional layer** — New layer adds `django-storages[s3]` for
  S3/MinIO static and media file storage. Available via `forge start` (option 6)
  and `forge add storage`.

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

[0.1.0]: https://github.com/k1lgor/django-forge/releases/tag/v0.1.0
