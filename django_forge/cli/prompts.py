"""Interactive prompts for project scaffold configuration.

Asks the user 3 questions (framework, database, optional layers),
then a summary confirmation.
"""

from rich.prompt import Confirm, Prompt

from django_forge.cli.console import console
from django_forge.cli.prefs import load_prefs

_FRAMEWORKS = {
    "1": ("DRF", "Django REST Framework - battle-tested, large ecosystem"),
    "2": ("Django-Ninja", "Modern, type-hint native, ~5x faster"),
    "3": ("Pure Django", "Templates + views, no API framework"),
}

_DATABASES = {
    "1": ("PostgreSQL (production) + SQLite (development)",
          "Production-ready, SQLite for fast local dev"),
    "2": ("SQLite only",
          "Simpler setup, no PostgreSQL dependency"),
}

_LAYERS = {
    "1": ("Docker", "Multi-stage build + Compose"),
    "2": ("Celery", "Background task queue (Redis required)"),
    "3": ("Email", "Mailpit (dev) / SMTP (prod)"),
    "4": ("Caching", "Redis cache backend"),
    "5": ("Social Auth", "Google + GitHub OAuth via allauth"),
    "6": ("S3 Storage", "S3/MinIO static + media file storage"),
}

_LAYER_KEY_MAP = {
    "1": "docker",
    "2": "celery",
    "3": "email",
    "4": "cache",
    "5": "social",
    "6": "storage",
}

_BASE_CONTEXT = {
    "project_name": "",
    "project_slug": "",
    "secret_key": "",
    "api": "pure",
    "db": "sqlite",
    "layers": [],
    "use_drf": False,
    "use_ninja": False,
    "use_pure_django": True,
    "has_docker": False,
    "has_celery": False,
    "has_email": False,
    "has_cache": False,
    "has_social": False,
    "has_storage": False,
}


def confirm_scaffold(
    project_name: str,
    api: str | None = None,
    db: str | None = None,
    layers: list[str] | None = None,
    no_input: bool = False,
) -> dict | None:
    """Show interactive prompts and return the scaffold context.

    Args:
        project_name: Name of the project to create.
        api: Default API framework choice (``None`` → use cached or hardcoded default).
        db: Default database choice (``None`` → use cached or hardcoded default).
        layers: Default optional layers list (``None`` → use cached or hardcoded default).
        no_input: If ``True``, skip all prompts and return defaults.

    Returns:
        The context dict for the renderer, or ``None`` if the user declined.
    """
    cached = load_prefs()

    if api is None:
        api = cached["api"]
    if db is None:
        db = cached["db"]
    if layers is None:
        layers = cached["layers"]

    assert api is not None
    assert db is not None
    assert layers is not None

    if no_input:
        return _build_context(
            project_name, api=api, db=db, layers=list(layers),
        )

    # Question 1: API Framework
    api = _ask_framework(default=api)

    # Question 2: Database
    db = _ask_database(default=db)

    # Question 3: Optional layers
    layers = _ask_layers(default=layers)

    context = _build_context(project_name, api, db, layers)

    # Summary
    console.print()
    console.print(
        "[forge.separator]───────────────────────────────────────[/]"
    )
    console.print()
    console.print(
        f"  [forge.primary]Project:[/]   [forge.highlight]{project_name}[/]"
    )
    console.print(
        f"  [forge.primary]Framework:[/] [forge.label]{_api_label(api)}[/]"
    )
    console.print(
        f"  [forge.primary]Database:[/]  [forge.label]{_db_label(db)}[/]"
    )
    layer_names = _layer_labels(layers)
    console.print(
        f"  [forge.primary]Layers:[/]    "
        f"[forge.label]{layer_names}[/]"
    )
    console.print()

    confirmed = Confirm.ask(
        "[forge.prompt]Looks good?[/]",
        default=True,
    )

    if not confirmed:
        console.print("[forge.muted]Aborted. No files were written.[/]")
        return None

    return context


def _build_context(
    project_name: str,
    api: str,
    db: str,
    layers: list[str],
) -> dict:
    """Build the scaffold context dict from raw values."""
    context = dict(_BASE_CONTEXT)
    context["project_name"] = project_name
    context["project_slug"] = project_name.replace("-", "_").replace(" ", "_")
    context["api"] = api
    context["db"] = db
    context["layers"] = list(layers)
    context["use_drf"] = api == "drf"
    context["use_ninja"] = api == "ninja"
    context["use_pure_django"] = api == "pure"
    context["has_docker"] = "docker" in layers
    context["has_celery"] = "celery" in layers
    context["has_email"] = "email" in layers
    context["has_cache"] = "cache" in layers
    context["has_social"] = "social" in layers
    context["has_storage"] = "storage" in layers
    return context


def _ask_framework(default: str = "pure") -> str:
    """Ask the user which API framework to use."""
    console.print()
    console.print("  [forge.primary]API Framework[/]")
    for key, (name, desc) in _FRAMEWORKS.items():
        console.print(f"  [forge.label]{key}.[/] {name}")
        console.print(f"     [forge.muted]{desc}[/]")

    default_key = "3"  # Pure Django
    if default == "drf":
        default_key = "1"
    elif default == "ninja":
        default_key = "2"

    choice = Prompt.ask(
        "  [forge.prompt]Which API framework? (1-3)[/]",
        choices=list(_FRAMEWORKS.keys()),
        default=default_key,
        show_choices=False,
    )

    mapping = {"1": "drf", "2": "ninja", "3": "pure"}
    return mapping[choice]


def _ask_database(default: str = "sqlite") -> str:
    """Ask the user which database setup to use."""
    console.print()
    console.print("  [forge.primary]Database[/]")
    for key, (name, desc) in _DATABASES.items():
        console.print(f"  [forge.label]{key}.[/] {name}")
        console.print(f"     [forge.muted]{desc}[/]")

    default_key = "2"  # SQLite only
    if default == "postgres":
        default_key = "1"

    choice = Prompt.ask(
        "  [forge.prompt]Which database? (1-2)[/]",
        choices=list(_DATABASES.keys()),
        default=default_key,
        show_choices=False,
    )

    mapping = {"1": "postgres", "2": "sqlite"}
    return mapping[choice]


def _ask_layers(default: list[str] | None = None) -> list[str]:
    """Ask the user which optional layers to include."""
    if default is None:
        default = []

    console.print()
    console.print("  [forge.primary]Optional Layers[/]")
    for key, (name, desc) in _LAYERS.items():
        indicator = "●" if _LAYER_KEY_MAP[key] in default else "○"
        console.print(f"  [forge.label]{key}.[/] {indicator} {name}")
        console.print(f"     [forge.muted]{desc}[/]")

    raw = Prompt.ask(
        "  [forge.prompt]"
        "Select optional layers"
        " (comma-separated numbers, or 0 for none)[/]",
        default="0",
    )

    selected: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part == "0" or not part:
            continue
        if part in _LAYER_KEY_MAP:
            selected.append(_LAYER_KEY_MAP[part])

    return selected


def _api_label(api: str) -> str:
    mapping = {
        "drf": "DRF - Django REST Framework",
        "ninja": "Django-Ninja",
        "pure": "Pure Django (no API)",
    }
    return mapping.get(api, api)


def _db_label(db: str) -> str:
    mapping = {
        "postgres": "PostgreSQL (prod) + SQLite (dev)",
        "sqlite": "SQLite only",
    }
    return mapping.get(db, db)


def _layer_labels(layers: list[str]) -> str:
    """Format layer list for display."""
    if not layers:
        return "none"
    label_map = {
        "docker": "Docker",
        "celery": "Celery",
        "email": "Email",
        "cache": "Caching",
        "social": "Social Auth",
        "storage": "S3 Storage",
    }
    return ", ".join(label_map.get(layer, layer) for layer in layers)
