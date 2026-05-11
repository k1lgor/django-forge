"""Adversarial tests for project tooling templates (Story 1.4)."""

import tempfile
from pathlib import Path

from django_forge.renderer import Renderer

PROJECT_TEMPLATES = (
    Path(__file__).resolve().parent.parent / "django_forge" / "templates"
)

MINIMAL_CONTEXT = {
    "project_name": "testproj",
    "project_slug": "testproj",
    "secret_key": "django-insecure-test-key",
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
# CI workflow structural checks
# ---------------------------------------------------------------------------


def test_ci_workflow_has_all_jobs() -> None:
    """CI workflow has lint, typecheck, and test jobs."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (
            target / ".github" / "workflows" / "ci.yml"
        ).read_text()
        assert "lint:" in content
        assert "typecheck:" in content
        assert "test:" in content
        # Each job uses ubuntu, macos, windows
        assert "ubuntu-latest" in content
        assert "macos-latest" in content
        assert "windows-latest" in content


def test_ci_workflow_uses_astral_setup_uv() -> None:
    """CI workflow uses astral-sh/setup-uv for uv installation."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (
            target / ".github" / "workflows" / "ci.yml"
        ).read_text()
        assert "astral-sh/setup-uv@v5" in content


def test_ci_workflow_python_version() -> None:
    """CI workflow uses Python 3.12."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (
            target / ".github" / "workflows" / "ci.yml"
        ).read_text()
        assert 'python-version: "3.12"' in content


# ---------------------------------------------------------------------------
# Makefile structural checks
# ---------------------------------------------------------------------------


def test_makefile_has_all_targets() -> None:
    """1.4.G — Makefile has all 7 required targets."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (target / "Makefile").read_text()
        required_targets = [
            "lint",
            "typecheck",
            "test",
            "check",
            "run",
            "migrate",
            "makemigrations",
        ]
        for t in required_targets:
            assert f"{t}:" in content, (
                f"Makefile missing target: {t}"
            )


def test_makefile_check_depends_on_all() -> None:
    """Makefile 'check' target has lint, typecheck, and test as dependencies."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (target / "Makefile").read_text()
        # Find lines that declare dependencies (have colons)
        for line in content.splitlines():
            if line.startswith("check:"):
                assert "lint" in line
                assert "typecheck" in line
                assert "test" in line
                break
        else:
            raise AssertionError("Makefile missing 'check:' target")


# ---------------------------------------------------------------------------
# Pre-commit config checks
# ---------------------------------------------------------------------------


def test_pre_commit_has_ruff_and_ty() -> None:
    """1.4.H — pre-commit has ruff and ty hooks."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (target / ".pre-commit-config.yaml").read_text()
        assert "ruff" in content
        assert "ty" in content
        assert "ruff-format" in content or "ruff format" in content


def test_pre_commit_repos_are_https() -> None:
    """Pre-commit repo URLs are https (not git@ or ssh)."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (target / ".pre-commit-config.yaml").read_text()
        assert "https://" in content
        assert "ssh://" not in content


# ---------------------------------------------------------------------------
# conftest.py checks
# ---------------------------------------------------------------------------


def test_conftest_has_pytest_configure() -> None:
    """conftest.py has pytest_configure function."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (target / "tests" / "conftest.py").read_text()
        assert "pytest_configure" in content
        assert "DJANGO_SETTINGS_MODULE" in content
        assert "config.settings.base" in content


def test_conftest_pytest_configure_is_valid() -> None:
    """pytest_configure function uses correct signature (no args)."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (target / "tests" / "conftest.py").read_text()
        assert "def pytest_configure()" in content


# ---------------------------------------------------------------------------
# test_example.py checks
# ---------------------------------------------------------------------------


def test_example_has_django_db_marker() -> None:
    """test_example.py uses @pytest.mark.django_db marker."""
    renderer = Renderer(PROJECT_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(MINIMAL_CONTEXT, target)
        content = (
            target / "tests" / "test_example.py"
        ).read_text()
        assert "pytest.mark.django_db" in content
        assert "django.conf import settings" in content


# ---------------------------------------------------------------------------
# pyproject.toml renders valid TOML for all configuration options
# ---------------------------------------------------------------------------


def test_pyproject_toml_all_options_toml_valid() -> None:
    """pyproject.toml renders valid TOML even with all options enabled."""
    import tomllib as _toml

    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx.update(
        use_drf=True,
        use_ninja=True,
        api="drf",
        has_docker=True,
        has_celery=True,
        has_email=True,
    )
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        content = (target / "pyproject.toml").read_text()
        _toml.loads(content)  # raises on invalid TOML


# ---------------------------------------------------------------------------
# Verify generated files have correct DJANGO_SETTINGS_MODULE
# ---------------------------------------------------------------------------


def test_pytest_config_has_correct_settings_module() -> None:
    """pytest config references the generated project's settings module."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = dict(MINIMAL_CONTEXT)
    ctx["project_slug"] = "my_custom_app"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        # Check pyproject.toml
        toml_content = (target / "pyproject.toml").read_text()
        assert "config.settings.base" in toml_content
        # Check conftest.py
        conftest_content = (
            target / "tests" / "conftest.py"
        ).read_text()
        assert "config.settings.base" in conftest_content
