"""``forge-django list`` command — show available options."""

from django_forge.cli.console import console
from django_forge.registry import LAYERS


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

    # Registry-driven rendering (design entry 32): label with its slug,
    # then the description.
    for layer in LAYERS:
        console.print(
            f"  [forge.label]{layer.label}[/]  [forge.muted](forge-django add {layer.slug})[/]"
        )
        console.print(f"    [forge.muted]{layer.description}[/]")
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
        ("Admin", "Custom User admin"),
        ("Logging", "Structured logging"),
        ("Static/media", "WhiteNoise for static files, django-storages ready"),
        ("Security", "CORS headers, security middleware, env-based secrets"),
    ]

    for name, desc in core_layers:
        console.print(f"  [forge.label]{name}[/]")
        console.print(f"    [forge.muted]{desc}[/]")
        console.print()
