# django-forge 🔨

**Scaffold production-ready Django projects with senior-architect best practices.**

`django-forge` is a CLI tool that generates complete, production-ready Django projects with a single command. It uses `uv` as the package manager and ships with modern tooling out of the box.

> **Status: Alpha** — `forge start` is under active development. Stay tuned.

## Quick start

```bash
# Install
uv tool install django-forge

# See available commands
forge --help

# Scaffold a new project (coming in v0.1)
forge start myproject
```

## Features (planned)

- **Framework choice** — Pick DRF, Django-Ninja, or pure Django at scaffold time
- **Core tooling** — Ruff (linting), basedpyright (type checking), pytest (testing)
- **Auth** — Custom user model, django-allauth, JWT / session auth
- **Database** — PostgreSQL (production) + SQLite (development)
- **Async** — ASGI via uvicorn
- **CI/CD** — GitHub Actions workflow included
- **Optional layers** — Docker, Celery, Email (toggleable)

## License

MIT
