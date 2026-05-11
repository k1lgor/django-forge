"""Add an optional layer to an existing project."""

from rich.console import Console

console = Console()


def add_layer(*, layer: str) -> None:
    """Add an optional layer to an existing forged project.

    This is a stub implementation for v0.1.0.
    Full implementation comes in Epic 6 (v0.2 scope).
    """
    console.print(
        f"[bold yellow]Coming in v0.2[/bold yellow] — "
        f"[dim]The '[bold]{layer}[/bold]' layer cannot be added yet. "
        f"This feature is planned for a future release.[/dim]"
    )
