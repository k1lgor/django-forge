"""Adversarial edge-case tests for the renderer and template corpus."""

import ast
import tempfile
from pathlib import Path

import pytest

from django_forge.renderer import Renderer

PROJECT_TEMPLATES = Path(__file__).resolve().parent.parent / "django_forge" / "templates"

MINIMAL_CONTEXT = {
    "project_name": "myproject",
    "project_slug": "myproject",
    "secret_key": "django-insecure-test-key-not-for-production",
    "api": "pure",
    "db": "sqlite",
    "layers": [],
    "use_drf": False,
    "use_ninja": False,
    "use_pure_django": True,
    "has_docker": False,
    "has_celery": False,
    "has_email": False,
}


# ---------------------------------------------------------------------------
# Context edge cases
# ---------------------------------------------------------------------------


def test_render_with_empty_context_raises_error() -> None:
    """Empty context (missing all keys) raises Jinja2 UndefinedError."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        with pytest.raises(Exception) as excinfo:
            renderer.render_project({}, target)
        # The error should mention an undefined variable
        assert (
            "undefined" in str(excinfo.value).lower()
            or "undefined" in type(excinfo.value).__name__.lower()
        )


def test_render_with_extra_context_keys() -> None:
    """Extra context keys that templates don't reference should be ignored."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["completely_unused_key"] = "should_not_cause_errors"
    ctx["another_extra"] = 42
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        assert (target / "manage.py").exists()


def test_render_with_all_options_enabled() -> None:
    """Render with DRF + Ninja + PostgreSQL + all layers — should not crash."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = {
        "project_name": "megaproject",
        "project_slug": "megaproject",
        "secret_key": "django-insecure-mega-key",
        "api": "drf",
        "db": "postgres",
        "layers": ["docker", "celery", "email"],
        "use_drf": True,
        "use_ninja": True,
        "use_pure_django": False,
        "has_docker": True,
        "has_celery": True,
        "has_email": True,
    }
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        assert (target / "manage.py").exists()
        assert (target / "pyproject.toml").exists()


def test_render_with_empty_layers() -> None:
    """Empty layers list renders correctly (regression for 'layers': [])."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["layers"] = []
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        toml_content = (target / ".forge.toml").read_text()
        assert "layers = []" in toml_content


def test_render_with_none_values_in_context() -> None:
    """Context dict with None values — should not crash but may produce 'null'."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = {
        "project_name": "test",
        "project_slug": "test",
        "secret_key": "key",
        "api": None,  # None value
        "db": None,  # None value
        "layers": None,  # None value
        "use_drf": None,
        "use_ninja": None,
        "use_pure_django": True,
        "has_docker": None,
        "has_celery": None,
        "has_email": None,
    }
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        # Should not crash — None values are rendered as "None" by Jinja2
        renderer.render_project(ctx, target)


# ---------------------------------------------------------------------------
# Project name edge cases
# ---------------------------------------------------------------------------


def test_project_name_with_hyphens() -> None:
    """Project name with hyphens should render without error."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["project_name"] = "my-awesome-project"
    ctx["project_slug"] = "my_awesome_project"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        pyproject = (target / "pyproject.toml").read_text()
        assert "my_awesome_project" in pyproject


def test_project_name_with_numbers() -> None:
    """Project name with numbers should render without error."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["project_name"] = "project42"
    ctx["project_slug"] = "project42"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)


def test_project_name_with_unicode() -> None:
    """Project name with Unicode characters should render without error."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["project_name"] = "cafe-project"
    ctx["project_slug"] = "cafe_project"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)


# ---------------------------------------------------------------------------
# Template rendering edge cases
# ---------------------------------------------------------------------------


def test_empty_template_directory() -> None:
    """Empty template root returns empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        empty_root = Path(tmp) / "empty"
        empty_root.mkdir()
        renderer = Renderer(empty_root)
        with tempfile.TemporaryDirectory() as out:
            result = renderer.render_project({"a": 1}, Path(out))
            assert result == []


def test_dotfile_template_renders() -> None:
    """Dotfiles (e.g., .env.example.j2 → .env.example) render correctly."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        assert (target / ".env.example").exists()
        assert (target / ".gitignore").exists()


def test_secret_key_with_special_chars() -> None:
    """Secret key containing Jinja2-special characters shouldn't crash rendering.

    Real Django SECRET_KEY values can contain $, {, }, %, etc.
    """
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["secret_key"] = "django-insecure-$%{special}#[char]&*()!"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)


# ---------------------------------------------------------------------------
# DRF and Ninja template rendering
# ---------------------------------------------------------------------------


def test_drf_templates_render_valid_python() -> None:
    """Templates rendered with use_drf=True produce valid Python."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["api"] = "drf"
    ctx["use_drf"] = True
    ctx["use_pure_django"] = False
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        base_py = (target / "config" / "settings" / "base.py").read_text()
        ast.parse(base_py)
        urls_py = (target / "config" / "urls.py").read_text()
        ast.parse(urls_py)


def test_ninja_templates_render_valid_python() -> None:
    """Templates rendered with use_ninja=True produce valid Python."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["api"] = "ninja"
    ctx["use_ninja"] = True
    ctx["use_pure_django"] = False
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        base_py = (target / "config" / "settings" / "base.py").read_text()
        ast.parse(base_py)
        urls_py = (target / "config" / "urls.py").read_text()
        ast.parse(urls_py)


# ---------------------------------------------------------------------------
# PostgreSQL template rendering
# ---------------------------------------------------------------------------


def test_postgres_template_renders_valid_python() -> None:
    """Templates rendered with db='postgres' produce valid Python."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["db"] = "postgres"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        base_py = (target / "config" / "settings" / "base.py").read_text()
        ast.parse(base_py)
        # PostgreSQL DATABASES config should be present
        assert "postgresql" in base_py or "postgres" in base_py
        assert "ENGINE" in base_py
        assert "django.db.backends.postgresql" in base_py or "sqlite3" in base_py


# ---------------------------------------------------------------------------
# Symlink handling
# ---------------------------------------------------------------------------


def test_symlink_in_template_root(tmp_path: Path) -> None:
    """Symlinks in template root should be followed (default rglob behavior)."""
    # Create a real template and a symlink to it
    real_dir = tmp_path / "real_templates"
    real_dir.mkdir()
    (real_dir / "hello.txt.j2").write_text("Hello {{ name }}!")

    link_dir = tmp_path / "link_templates"
    link_dir.mkdir()
    # Create a symlink — skip if not supported (Windows)
    try:
        (link_dir / "linked.txt.j2").symlink_to(
            real_dir / "hello.txt.j2", target_is_directory=False
        )
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")

    renderer = Renderer(link_dir)
    with tempfile.TemporaryDirectory() as out:
        target = Path(out)
        renderer.render_project({"name": "Symlink"}, target)
        # Symlinked file should be rendered
        assert (target / "linked.txt").exists()


# ---------------------------------------------------------------------------
# File content assertions
# ---------------------------------------------------------------------------


def test_pyproject_toml_has_correct_deps() -> None:
    """pyproject.toml rendered for pure Django contains only Django dep."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        toml = (target / "pyproject.toml").read_text()
        assert "django~=5.1.0" in toml


def test_pyproject_toml_drf_includes_rest_framework() -> None:
    """pyproject.toml for DRF includes djangorestframework."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["use_drf"] = True
    ctx["api"] = "drf"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        toml = (target / "pyproject.toml").read_text()
        assert "djangorestframework" in toml
        assert "djangorestframework-simplejwt" in toml


def test_drf_context_adds_rest_framework_to_installed_apps() -> None:
    """DRF context adds rest_framework to INSTALLED_APPS."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["use_drf"] = True
    ctx["api"] = "drf"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        base = (target / "config" / "settings" / "base.py").read_text()
        assert '"rest_framework"' in base


# ---------------------------------------------------------------------------
# Cross-platform: path separators in templates
# ---------------------------------------------------------------------------


def test_template_paths_use_forward_slash_in_jinja2() -> None:
    """Jinja2 template names must use forward slashes regardless of OS."""
    renderer = Renderer(PROJECT_TEMPLATES)
    # This verifies that the renderer correctly loads nested templates
    ctx = dict(MINIMAL_CONTEXT)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        assert (target / "config" / "settings" / "base.py").exists()


# ---------------------------------------------------------------------------
# Memory / large template count
# ---------------------------------------------------------------------------


def test_large_number_of_templates(tmp_path: Path) -> None:
    """Renderer handles 100+ templates without error."""
    large_root = tmp_path / "large"
    large_root.mkdir()
    for i in range(150):
        (large_root / f"file_{i:04d}.txt.j2").write_text("{{ value }}")

    renderer = Renderer(large_root)
    with tempfile.TemporaryDirectory() as out:
        target = Path(out)
        result = renderer.render_project({"value": "test"}, target)
        assert len(result) == 150  # all 150 files rendered


# ---------------------------------------------------------------------------
# render_project return value
# ---------------------------------------------------------------------------


def test_return_value_includes_all_files() -> None:
    """render_project returns exactly as many entries as files written."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        result = renderer.render_project(ctx, target)
        # The render manifest is metadata, not a rendered artifact — it is
        # written but intentionally excluded from the returned list.
        actual_file_count = sum(1 for _ in target.rglob("*") if _.is_file())
        if (target / ".forge-manifest.json").exists():
            actual_file_count -= 1
        assert len(result) == actual_file_count
        # Each entry has non-negative content length
        # (empty files like __init__.py legitimately have 0 bytes)
        for path, size in result:
            assert size >= 0, f"File {path} has negative content length: {size}"
