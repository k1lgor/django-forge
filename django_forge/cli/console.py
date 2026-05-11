"""Shared Rich console with the forge design theme."""

from rich.console import Console
from rich.theme import Theme

forge_theme = Theme({
    "forge.brand":      "bold bright_yellow",
    "forge.primary":    "bold orange1",
    "forge.accent":     "bold orange_red1",
    "forge.success":    "bold green",
    "forge.error":      "bold red",
    "forge.warning":    "bold yellow",
    "forge.info":       "bold blue",
    "forge.muted":      "dim white",
    "forge.prompt":     "bold cyan",
    "forge.highlight":  "bold white",
    "forge.label":      "dim orange1",
    "forge.separator":  "bright_black",
})

console = Console(theme=forge_theme)
