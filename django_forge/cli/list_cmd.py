"""``forge list`` command — show available options."""

from django_forge.cli.console import console


def list_options() -> None:
    """Print all available frameworks, optional layers, and core layers."""
    console.print()
    console.print("[forge.separator]=======================================[/]")
    console.print("  [forge.brand]django-forge - Available Options[/]")
    console.print("[forge.separator]=======================================[/]")
    console.print()
    _print_frameworks()
    console.print()
    _print_optional_layers()
    console.print()
    _print_core_layers()
    console.print()


def _print_frameworks() -> None:
    """Print available API frameworks."""
    console.print("  [forge.primary]Available Frameworks[/]")
    console.print()

    frameworks = [
        (
            "DRF",
            "Django REST Framework - the classic choice.",
            "Mature, large ecosystem, serializer-based.",
            "JWT auth (simplejwt), browsable API, filtering.",
        ),
        (
            "Django-Ninja",
            "Modern, type-hint native, Pydantic-based.",
            "~5x faster request handling than DRF.",
            "JWT auth, OpenAPI docs, async views.",
            "recommended for new projects",
        ),
        (
            "Pure Django",
            "No API framework. Traditional Django views + templates.",
            "Best for: server-rendered apps, admin-heavy projects.",
            "Session-based auth via allauth.",
        ),
    ]

    for fw in frameworks:
        name = fw[0]
        console.print(f"  [forge.label]{name}[/]")

        if len(fw) > 4 and fw[4]:
            console.print(f"    [forge.accent]* {fw[4]}[/]")

        for line in fw[1:4]:
            if line:
                console.print(f"    [forge.muted]{line}[/]")
        console.print()


def _print_optional_layers() -> None:
    """Print available optional layers."""
    console.print("  [forge.primary]Available Optional Layers[/]")
    console.print()

    layers = [
        ("Docker", "Multi-stage Dockerfile + Docker Compose (PostgreSQL, app)"),
        ("Celery", "Background task queue (requires Redis)"),
        ("Email", "Mailpit (dev) / SMTP (prod) configuration"),
        ("Caching", "Redis cache backend (django.core.cache.backends.redis)"),
        ("Social Auth", "Google + GitHub OAuth via django-allauth"),
        ("S3 Storage", "django-storages[s3] — static + media files on S3/MinIO"),
        ("Health Check", "django-health-check — /healthz for load balancers"),
        ("Audit Trail", "django-simple-history — record every model change"),
        ("Backup", "django-dbbackup — nightly DB dumps + restore drill"),
        ("Seed Data", "factory-boy dev data + manage.py seed command"),
        ("Preflight", "manage.py preflight — deploy check before pushing"),
    ]

    for name, desc in layers:
        console.print(f"  [forge.label]{name}[/]")
        console.print(f"    [forge.muted]{desc}[/]")
        console.print()


def _print_core_layers() -> None:
    """Print always-included core layers."""
    console.print("  [forge.primary]Core Layers (always included)[/]")
    console.print()

    core_layers = [
        ("Python tooling", "uv, pyproject.toml, Python 3.12+"),
        ("Linting & type checking", "ruff (linter + formatter), ty (type checker)"),
        ("Testing", "pytest, pytest-django, coverage, factory_boy"),
        ("Auth", "Custom user model, allauth, JWT / session auth"),
        ("Database", "PostgreSQL (prod) / SQLite (dev), migration defaults"),
        ("Async", "ASGI via uvicorn, async views, async ORM support"),
        ("CI/CD", "GitHub Actions: lint, type-check, test, deploy-check"),
        ("Admin", "Custom User admin, admin sortable, django-unsign"),
        ("Logging", "Structured logging, Sentry integration (DSN-gated)"),
        ("Static/media", "WhiteNoise for static files, django-storages ready"),
        ("Security", "CORS headers, security middleware, env-based secrets"),
    ]

    for name, desc in core_layers:
        console.print(f"  [forge.label]{name}[/]")
        console.print(f"    [forge.muted]{desc}[/]")
        console.print()
