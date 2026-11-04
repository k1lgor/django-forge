"""Interactive prompts for project scaffold configuration.

Asks the user 3 questions (framework, database, optional layers),
then a summary confirmation.
"""

from rich.prompt import Confirm, Prompt

from django_forge.cli.console import console
from django_forge.cli.prefs import load_prefs
from django_forge.project import build_context
from django_forge.registry import LAYERS

_FRAMEWORKS = {
    "1": ("DRF", "Django REST Framework - battle-tested, large ecosystem"),
    "2": ("Django-Ninja", "Modern, type-hint native, ~5x faster"),
    "3": ("Pure Django", "Templates + views, no API framework"),
}

_DATABASES = {
    "1": (
        "PostgreSQL (production) + SQLite (development)",
        "Production-ready, SQLite for fast local dev",
    ),
    "2": ("SQLite only", "Simpler setup, no PostgreSQL dependency"),
}

# Layer menu derived from the single registry (design entry 35): menu keys,
# labels and descriptions all come from ``django_forge.registry.LAYERS``.
_LAYERS = {layer.menu_key: (layer.label, layer.description) for layer in LAYERS}
_LAYER_KEY_MAP = {layer.menu_key: layer.id for layer in LAYERS}


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
    if no_input:
        # Decision 2 / entry 27: --no-input never reads the prefs cache —
        # fixed defaults, overridden by whatever options the caller passed.
        return _build_context(
            project_name,
            api=api or "drf",
            db=db or "postgres",
            layers=list(layers or []),
        )

    cached = load_prefs()
    if api is None:
        api = cached["api"]
    if db is None:
        db = cached["db"]
    if layers is None:
        layers = cached["layers"]

    if api is None or db is None or layers is None:
        console.print("  [forge.error]Could not determine scaffold defaults.[/]")
        return None

    # Question 1: API Framework
    api = _ask_framework(default=api)

    # Question 2: Database
    db = _ask_database(default=db)

    # Question 3: Optional layers
    layers = _ask_layers(default=layers)

    context = _build_context(project_name, api, db, layers)

    # Summary
    console.print()
    console.print("[forge.separator]───────────────────────────────────────[/]")
    console.print()
    console.print(f"  [forge.primary]Project:[/]   [forge.highlight]{project_name}[/]")
    console.print(f"  [forge.primary]Framework:[/] [forge.label]{_api_label(api)}[/]")
    console.print(f"  [forge.primary]Database:[/]  [forge.label]{_db_label(db)}[/]")
    layer_names = _layer_labels(layers)
    console.print(f"  [forge.primary]Layers:[/]    [forge.label]{layer_names}[/]")
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
    """Build the scaffold context from raw values via the shared builder."""
    return build_context(
        {"project_name": project_name, "api": api, "db": db, "layers": list(layers)}
    )


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

    default_numbers = (
        ",".join(key for key, layer_id in _LAYER_KEY_MAP.items() if layer_id in (default or []))
        or "0"
    )

    while True:
        raw = Prompt.ask(
            "  [forge.prompt]Select optional layers (comma-separated numbers, or 0 for none)[/]",
            default=default_numbers,
        )
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        if all(part == "0" or part in _LAYER_KEY_MAP for part in parts):
            break
        console.print(
            "  [forge.error]Invalid selection — use numbers 1-11"
            " (comma-separated) or 0 for none.[/]"
        )

    return [_LAYER_KEY_MAP[part] for part in parts if part != "0"]


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
        "healthcheck": "Health Check",
        "audit": "Audit Trail",
        "backup": "Backup",
        "seed": "Seed Data",
        "preflight": "Preflight",
    }
    return ", ".join(label_map.get(layer, layer) for layer in layers)
