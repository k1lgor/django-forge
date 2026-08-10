# django-forge 🔨

**Ask 3 questions. Get a production-ready Django project.**

`forge` scaffolds complete, immediately runnable Django projects with
senior-architect best practices — custom User model, allauth auth,
ruff + ty tooling, GitHub Actions CI/CD, and your choice of API
framework, database, and optional layers. All in under a minute.

```bash
uv tool install django-forge
forge start myproject
```

What you get:

```
myproject/
├── config/settings/     # base.py, dev.py, prod.py
├── apps/accounts/       # Custom User, allauth, views
├── templates/           # base.html (extends as needed)
├── pyproject.toml       # ruff, ty, pytest configured
├── Dockerfile           # (if you chose Docker)
└── .github/workflows/   # CI: lint, type-check, test, deploy
```

## Usage

```
$ forge start myproject
$ forge --help
$ forge list
$ forge start myproject --no-input     # for CI
$ forge add docker                      # add layer to existing project
$ forge add celery
$ forge add email
```

The wizard asks three questions:

1. **API Framework** — DRF (JWT + browsable API), Django-Ninja (OpenAPI docs, faster), or Pure Django (templates + session auth)
2. **Database** — PostgreSQL (production) + SQLite (development), or SQLite only
3. **Optional Layers** — Docker (multi-stage build + Compose), Celery (Redis broker), Email (Mailpit dev / SMTP prod)

After answering, `forge` generates all files, runs `uv sync`, migrates the database, and runs `check --deploy`.

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
  1. Docker    Multi-stage build + Compose
  2. Celery    Background task queue (Redis)
  3. Email     Mailpit (dev) / SMTP (prod)

  Project:   myproject
  Framework: DRF
  Database:  PostgreSQL (prod) + SQLite (dev)
  Layers:    Docker

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
| **Admin** | Custom User admin, admin sortable, django-unsign |
| **Logging** | Structured logging, Sentry DSN-gated |
| **Static/media** | WhiteNoise, django-storages-ready |
| **Security** | CORS headers, env-based secrets, HSTS in production |

## Optional layers

| Layer | What it adds |
|---|---|
| **Docker** | Multi-stage `Dockerfile` (uv build), `compose.yaml` with app + db + optional redis/mailpit |
| **Celery** | `config/celery.py`, `tasks.py`, Redis broker + cache, deps: `celery~=5.4`, `redis>=5.0` |
| **Email** | Mailpit (dev) / SMTP (prod) config, email env vars in `.env.example` |

## Adding layers later — `forge add`

Already have a project? Run `forge add <layer>` from its root directory.
Docker, Celery, or Email layers can be added after scaffolding. The command
detects your project context from `.forge.toml`, confirms before overwriting
any existing files, and updates the layer tracking.

```bash
cd myproject
forge add docker     # adds Dockerfile + compose.yaml + .dockerignore
forge add celery    # adds worker, tasks, patches settings
forge add email     # patches settings with email config
```

## Automation

`--no-input` skips all prompts and uses sensible defaults (DRF, PostgreSQL+SQLite, no layers). CI environments (`CI=true`, `GITHUB_ACTIONS=true`) auto-activate this mode.

```bash
forge start myproject --no-input
```

## Installation

```bash
uv tool install django-forge
```

**Requires:** Python 3.10+ for the CLI tool, Python 3.12+ for generated projects.  
**Package manager:** `uv` (install from [astral.sh/uv](https://astral.sh/uv)).

## License

MIT
