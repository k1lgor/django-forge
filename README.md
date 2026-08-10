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

`forge` asks three questions:

1. **API Framework** — DRF (JWT + browsable API), Django-Ninja (OpenAPI
   docs, faster), or Pure Django (templates + session auth)
2. **Database** — PostgreSQL (production) + SQLite (development), or SQLite only
3. **Optional Layers** — 11 layers, any combination (see below)

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

## What ships in every project

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

## Optional layers

| Layer | What it adds |
|---|---|
| **Docker** | Multi-stage `Dockerfile` (uv build) + `gunicorn`, `compose.yaml` with app + db + optional redis/mailpit, `.dockerignore` |
| **Celery** | `config/celery.py`, `tasks.py`, Redis broker + cache, deps: `celery~=5.4`, `redis>=5.0` |
| **Email** | Mailpit (dev) / SMTP (prod) config, email env vars in `.env.example` |
| **Caching** | Redis cache backend (`django.core.cache.backends.redis.RedisCache`) |
| **Social Auth** | `SOCIALACCOUNT_PROVIDERS` for Google + GitHub, provider env vars |
| **S3 Storage** | `django-storages[s3]` — static + media on S3/MinIO |
| **Health Check** | `django-health-check` at `/healthz/` — DB always, cache/broker when those layers exist |
| **Audit Trail** | `django-simple-history` — `HistoricalRecords` on the User, history middleware, `SimpleHistoryAdmin` |
| **Backup** | `django-dbbackup` — nightly dumps to S3 (with storage) or `backups/`, `make backup` / `make restore` |
| **Seed Data** | factory-boy `UserFactory` + `manage.py seed`, `make seed` |
| **Preflight** | `manage.py preflight` — `check --deploy` + pending migrations + `migrate --check`, `make preflight` |

## Adding layers later — `forge add`

Already have a project? Run `forge add <layer>` from its root directory —
works for **all 11 layers**. The command detects your project context from
`.forge.toml`, confirms before overwriting any files, and updates the
layer tracking.

```bash
cd myproject
forge add docker      # Dockerfile + compose.yaml + .dockerignore
forge add healthcheck # /healthz endpoint
forge add backup      # nightly DB dumps
```

**Your edits survive.** Every generated file is hashed into a
`.forge-manifest.json`. On `forge add` / `forge upgrade`, forge refreshes
files it still owns and **skips files you modified, byte for byte** — and
the `SECRET_KEY` is read back from your project instead of being
regenerated. `forge upgrade` re-applies the latest templates to an
existing project with the same protection.

## Automation

`--no-input` skips all prompts and uses sensible defaults (DRF,
PostgreSQL + SQLite, no layers). CI environments (`CI=true`,
`GITHUB_ACTIONS=true`) auto-activate this mode.

```bash
forge start myproject --no-input
```

## Repository layout

```
django_forge/          # the forge CLI package
├── cli/                # start, add, upgrade, list commands + installer
├── renderer.py         # Jinja2 engine + .forge-manifest.json ownership ledger
└── templates/          # the Jinja2 template tree for generated projects
site/                   # Svelte 5 landing page (GitHub Pages)
tests/                  # pytest suite (389 tests)
.github/workflows/
├── ci.yml              # tooling CI: ruff, ty, pytest (3 OS × 3 Python)
└── deploy-site.yml     # Pages deploy — triggers on site/ changes only
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
