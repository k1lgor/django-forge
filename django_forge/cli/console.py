"""Shared Rich console with the forge design theme."""

from rich.console import Console
from rich.theme import Theme

forge_theme = Theme(
    {
        "forge.brand": "bold bright_yellow",
        "forge.primary": "bold orange1",
        "forge.accent": "bold orange_red1",
        "forge.success": "bold green",
        "forge.error": "bold red",
        "forge.warning": "bold yellow",
        "forge.info": "bold blue",
        "forge.muted": "dim white",
        "forge.prompt": "bold cyan",
        "forge.highlight": "bold white",
        "forge.label": "dim orange1",
        "forge.separator": "bright_black",
    }
)

# legacy_windows=False: rich renders with ANSI instead of Win32 console API
# calls. On Windows, the Win32 path raises OSError [Errno 22] when the
# console handle is a broken/closed pipe (e.g. `forge list | Select -First`)
# because that failure is not BrokenPipeError.
console = Console(theme=forge_theme, legacy_windows=False)
