# django-forge 🔨

**Ask 3 questions. Get a production-ready Django project.**

`forge` scaffolds complete, immediately runnable Django projects with
senior-architect best practices — custom User model, allauth auth,
ruff + ty tooling, GitHub Actions CI/CD, and your choice of API
framework, database, and 11 optional layers. All in under a minute.

![CI](https://github.com/k1lgor/django-forge/actions/workflows/ci.yml/badge.svg)

```bash
uv tool install django-forge
forge start myproject
```

## About this repository

This repository contains **two things**:

1. **`django_forge/`** — the forge CLI tool and its Jinja2 template tree
   (the scaffolder itself).
2. **`site/`** — the project's landing page, a Svelte 5 + Vite single-page
   site deployed to GitHub Pages: <https://k1lgor.github.io/django-forge/>

Both live in this repo and are tested separately: the tooling CI runs on
`django_forge/` + `tests/` changes, and a dedicated workflow deploys the
site whenever `site/` changes. See [Repository layout](#repository-layout).

## Quick start

```bash
uv tool install django-forge   # install the CLI
forge start myproject          # answer 3 questions
cd myproject
uv run manage.py runserver     # start developing
```

`forge start` runs `uv sync`, creates migrations, migrates the database,
and runs `check --deploy` — your project is runnable the moment the
success banner prints.

## The wizard

`forge` asks three questions and confirms your choices before generating
anything. Every option is listed below.

### 1 · API Framework

| # | Option | What you get |
|---|---|---|
| 1 | **DRF** — Django REST Framework | The classic choice. Mature, large ecosystem, serializer-based. JWT auth (`djangorestframework-simplejwt`), browsable API, filtering. |
| 2 | **Django-Ninja** | Modern, type-hint native, Pydantic-based. ~5x faster request handling than DRF. JWT auth, OpenAPI docs, async views. *Recommended for new projects.* |
| 3 | **Pure Django** | No API framework. Traditional Django views + templates. Best for server-rendered apps and admin-heavy projects. Session-based auth via allauth. |

### 2 · Database

| # | Option | What you get |
|---|---|---|
| 1 | **PostgreSQL (prod) + SQLite (dev)** | Production-ready Postgres configuration via `DATABASE_URL`, with SQLite for fast local development. |
| 2 | **SQLite only** | Simpler setup, no PostgreSQL dependency. |

### 3 · Optional layers (multi-select — comma-separated numbers, or `0` for none)

| # | Layer | Description |
|---|---|---|
| 1 | Docker | Multi-stage build + Compose |
| 2 | Celery | Background task queue (Redis required) |
| 3 | Email | Mailpit (dev) / SMTP (prod) |
| 4 | Caching | Redis cache backend |
| 5 | Social Auth | Google + GitHub OAuth via allauth |
| 6 | S3 Storage | S3/MinIO static + media file storage |
| 7 | Health Check | `/healthz` endpoint for load balancers |
| 8 | Audit Trail | Record every model change (django-simple-history) |
| 9 | Backup | Nightly DB backups (django-dbbackup) |
| 10 | Seed Data | Factory-based dev data seeding |
| 11 | Preflight | Pre-deploy safety checks command |

The wizard looks like this:

```
=== FORGE v0.3.0 - django project scaffolder ===

  Forge your Django project:  myproject

  ◆ API Framework
  1. DRF       Django REST Framework - battle-tested
  2. Ninja     Modern, type-hint native, ~5x faster
  3. Pure      Templates + views, no API framework

  ◆ Database
  1. Postgres  Production (PostgreSQL) + dev (SQLite)
  2. SQLite    Simpler, no PostgreSQL dependency

  ◆ Optional Layers
  1. Docker         Multi-stage build + Compose
  2. Celery         Background task queue (Redis)
  3. Email          Mailpit (dev) / SMTP (prod)
  4. Caching        Redis cache backend
  5. Social Auth    Google + GitHub OAuth via allauth
  6. S3 Storage     S3/MinIO static + media file storage
  7. Health Check   /healthz for load balancers
  8. Audit Trail    Record every model change
  9. Backup         Nightly DB dumps + restore drill
  10. Seed Data     Factory-based dev data seeding
  11. Preflight     Pre-deploy safety checks command

  Project:   myproject
  Framework: DRF
  Database:  PostgreSQL (prod) + SQLite (dev)
  Layers:    Docker, Celery

  Looks good? [Y/n]
```

## CLI reference

| Command | Description |
|---|---|
| `forge start <project-name>` | Create a new Django project. Interactive wizard, or `--no-input` for defaults. |
| `forge list` | Show all available frameworks, optional layers, and core layers. |
| `forge add <layer>` | Add an optional layer to an existing project (works for all 11). |
| `forge upgrade` | Re-apply the latest templates to an existing project. |
| `forge --version` / `-V` | Print the forge version. |
| `forge --help` / `-h` | Show help. `forge` with no arguments also shows help. |

### `forge start` flags

| Flag | Description |
|---|---|
| `--no-input` | Skip all prompts and use sensible defaults (DRF, PostgreSQL + SQLite, no layers). Auto-activates in CI. |

### `forge add` behavior

Runs from inside an existing project. It:
- validates the layer name (`docker`, `celery`, `email`, `cache`, `social`,
  `storage`, `healthcheck`, `audit`, `backup`, `seed`, `preflight`),
- detects the project from `.forge.toml` ("Not a forge project" otherwise),
- skips layers that are already installed,
- lists every file it will overwrite and asks for confirmation,
- and preserves your existing layers and settings.

## Optional layers (all 11)

| Layer | What it adds | Deps |
|---|---|---|
| **Docker** | Multi-stage `Dockerfile` (uv build), `compose.yaml` with app + db + optional redis/mailpit, `.dockerignore`, gunicorn wired into the image | `gunicorn~=23.0` |
| **Celery** | `config/celery.py`, `apps/accounts/tasks.py`, Redis broker + cache settings, worker-ready `__init__.py` | `celery~=5.4.0`, `redis>=5.0` |
| **Email** | Mailpit (dev) / SMTP (prod) settings, email env vars in `.env.example`, Mailpit Compose service | — |
| **Caching** | Redis cache backend (`django.core.cache.backends.redis.RedisCache`) | `redis>=5.0` |
| **Social Auth** | `SOCIALACCOUNT_PROVIDERS` for Google + GitHub, provider env vars | — |
| **S3 Storage** | `STORAGES` pointing at `storages.backends.s3.S3Storage`, `AWS_*` settings + env vars, S3 media URL | `django-storages[s3]` |
| **Health Check** | `django-health-check` at `/healthz/` — DB check always, cache/broker checks when those layers exist | `django-health-check~=3.18` |
| **Audit Trail** | `django-simple-history` — `HistoricalRecords` on the User model, `HistoryRequestMiddleware`, `SimpleHistoryAdmin` | `django-simple-history` |
| **Backup** | `django-dbbackup` — dumps to S3 when the storage layer is present, else `backups/`; `make backup` / `make restore` | `django-dbbackup` |
| **Seed Data** | factory-boy `UserFactory` + `manage.py seed`, `make seed` | factory-boy (dev) |
| **Preflight** | `manage.py preflight` — `check --deploy`, pending-migrations check, `migrate --check`; `make preflight` | — |

## Core layers (always included)

| Layer | What's included |
|---|---|
| **Python tooling** | `uv`, `pyproject.toml`, Python 3.12+ |
| **Linting & types** | `ruff` (linter + formatter), `ty` (type checker) |
| **Testing** | `pytest`, `pytest-django`, `coverage`, `factory_boy` |
| **Auth** | Custom User model (email login), `django-allauth`, JWT or session |
| **Database** | PostgreSQL (prod) + SQLite (dev), migration defaults |
| **Async** | ASGI via `uvicorn`, async views, async ORM support |
| **CI/CD** | GitHub Actions: lint, type-check, test, deploy-check |
| **Admin** | Custom User admin |
| **Logging** | Structured logging |
| **Static/media** | WhiteNoise, django-storages-ready |
| **Security** | CORS headers, env-based secrets, HSTS in production |

## What a generated project looks like

```
myproject/
├── manage.py
├── pyproject.toml          # deps, ruff, ty, pytest configured
├── Makefile                # see commands below
├── .env.example            # all environment variables documented
├── .gitignore              # .env ignored, .env.example tracked
├── .forge.toml             # layer tracking — read by forge add/upgrade
├── .forge-manifest.json    # ownership ledger — keeps your edits safe
├── .pre-commit-config.yaml
├── config/
│   ├── settings/           # base.py, dev.py, prod.py (split correctly)
│   ├── urls.py, wsgi.py, asgi.py
│   └── celery.py           # (with the Celery layer)
├── apps/accounts/          # custom User, allauth, views, admin, signals
│   ├── factories.py        # (with Seed Data)
│   └── management/commands/  # seed.py, preflight.py (layers)
├── templates/              # base.html + accounts/* (Pure Django)
├── tests/                  # pytest-django wired
├── static/, media/
├── Dockerfile, compose.yaml, .dockerignore   # (with Docker)
└── .github/workflows/ci.yml
```

### Makefile commands (generated project)

| Command | Description |
|---|---|
| `make lint` | Run ruff linter + formatter check |
| `make typecheck` | Run `ty` type checker |
| `make test` | Run pytest |
| `make check` | lint + typecheck + test |
| `make run` | `manage.py runserver` |
| `make migrate` / `make makemigrations` | Database management |
| `make seed` | Create sample users (Seed Data layer) |
| `make preflight` | Pre-deploy checks (Preflight layer) |
| `make backup` / `make restore` | DB dumps / restore (Backup layer) |

### Environment variables

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Cryptographic signing key (env-driven via pydantic-settings) |
| `DJANGO_SETTINGS_MODULE` | `config.settings.base` by default |
| `DJANGO_DEBUG` | `true` in development, `false` in production |
| `DATABASE_URL` | PostgreSQL URL in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames (env-driven, never hardcoded `*`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |
| `DOCKER` | `true` when running in Docker (Docker layer) |
| `MAILPIT_SMTP_HOST` / `_PORT` / `MAILPIT_API_URL` | Mailpit (Email layer) |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP (Email layer) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth (Social Auth layer) |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth (Social Auth layer) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_STORAGE_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL` / `AWS_S3_REGION_NAME` | S3/MinIO (S3 Storage layer) |
| `SENTRY_DSN` | Optional — leave empty to disable |

## Adding layers later — `forge add`

Already have a project? Run `forge add <layer>` from its root directory —
works for **all 11 layers**.

```bash
cd myproject
forge add docker      # Dockerfile + compose.yaml + .dockerignore
forge add healthcheck # /healthz endpoint
forge add backup      # nightly DB dumps
```

## `forge upgrade`

Re-applies the latest templates to an existing project. It reads your
`.forge.toml`, lists every file it would overwrite, and asks for
confirmation before touching anything.

**Your edits survive.** Every generated file is hashed into a
`.forge-manifest.json`. On `forge add` / `forge upgrade`, forge refreshes
files it still owns and **skips files you modified, byte for byte** — and
the `SECRET_KEY` is read back from your project instead of being
regenerated.

## Automation

`--no-input` skips all prompts and uses sensible defaults (DRF,
PostgreSQL + SQLite, no layers). CI environments (`CI=true`,
`GITHUB_ACTIONS=true`) auto-activate this mode — perfect for pipelines.

```bash
forge start myproject --no-input
```

## Landing page

The landing page at <https://k1lgor.github.io/django-forge/> is a
terminal-styled single-page site built with **Svelte 5 + Vite** (~23 kB
gzip JS, no images or fonts, no-JS fallback). It features a boot-sequence
hero, an interactive **forge simulator** that builds a real project tree
from the 3 wizard questions, and the 11 layers shown as expandable cards
with the actual generated files.

```bash
cd site
npm install
npm run dev        # local dev at http://localhost:5173
npm run build      # static output in site/dist
```

The site deploys automatically to GitHub Pages whenever a push touches
`site/**` (enable Pages in repo settings with "Source: GitHub Actions").

## Repository layout

```
django_forge/          # the forge CLI package
├── cli/                # start, add, upgrade, list commands + installer
├── renderer.py         # Jinja2 engine + .forge-manifest.json ownership ledger
└── templates/          # the Jinja2 template tree for generated projects
site/                   # Svelte 5 landing page (GitHub Pages)
tests/                  # pytest suite
.github/workflows/
├── ci.yml              # tooling CI: ruff, ty, pytest (3 OS × 3 Python)
└── deploy-site.yml     # Pages deploy — triggers on site/ changes only
```

## Development

```bash
uv sync --all-extras --dev      # install dev deps
uv run pytest                   # run the test suite
uv run ruff check .             # lint
uv run ruff format --check .    # formatting
uv run ty check django_forge    # type check
```

## Installation

```bash
uv tool install django-forge
```

**Requires:** Python 3.10+ for the CLI tool, Python 3.12+ for generated projects.
**Package manager:** `uv` (install from [astral.sh/uv](https://astral.sh/uv)).

## License

MIT
