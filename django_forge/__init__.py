"""django-forge: Scaffold production-ready Django projects with senior-architect best practices."""

from importlib.metadata import PackageNotFoundError, version

from django_forge.renderer import Renderer

__all__ = ["Renderer"]

try:
    __version__ = version("forge-django")
except PackageNotFoundError:  # pragma: no cover - source tree without installed metadata
    __version__ = "0.4.0"
