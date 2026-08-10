"""Tests for the Jinja2 template rendering engine."""

import ast
import tempfile
from pathlib import Path

import pytest

from django_forge import __version__ as _forge_version
from django_forge.renderer import Renderer

FIXTURE_TEMPLATES = Path(__file__).resolve().parent / "fixtures" / "templates"
PROJECT_TEMPLATES = Path(__file__).resolve().parent.parent / "django_forge" / "templates"

# Standard context dict from architecture.md §3.3
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
    "has_cache": False,
    "has_social": False,
    "has_storage": False,
    "forge_version": _forge_version,
}


# ---------------------------------------------------------------------------
# Renderer construction
# ---------------------------------------------------------------------------


def test_renderer_accepts_path() -> None:
    """1.2.A — Renderer(template_root) accepts a Path and creates a Jinja2 env."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    assert renderer.template_root == FIXTURE_TEMPLATES
    assert renderer._env is not None


def test_renderer_with_nonexistent_path() -> None:
    """Renderer raises FileNotFoundError for missing template root."""
    with pytest.raises(FileNotFoundError):
        Renderer(Path("/nonexistent/path"))


# ---------------------------------------------------------------------------
# Rendering .j2 templates
# ---------------------------------------------------------------------------


def test_render_simple_template() -> None:
    """1.2.B — Simple .j2 file is rendered and .j2 suffix is stripped."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project({"name": "World"}, target)

        output = target / "simple.txt"
        assert output.exists()
        assert output.read_text().strip() == "Hello, World!"


def test_rendered_files_list() -> None:
    """1.2.J — render_project returns list of (Path, int) tuples."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        written = renderer.render_project({"name": "Test"}, target)

        assert isinstance(written, list)
        assert len(written) > 0
        for path, size in written:
            assert isinstance(path, Path)
            assert isinstance(size, int)
            assert size > 0


def test_nested_template_renders() -> None:
    """Nested template renders with correct path."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project({"name": "X", "greeting": "Hi"}, target)

        output = target / "nested" / "hello.txt"
        assert output.exists()
        assert output.read_text().strip() == "Nested: Hi"


def test_j2_suffix_stripped() -> None:
    """1.2.B — Output files have .j2 suffix removed, other extensions preserved."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project({"name": "X"}, target)

        # simple.txt.j2 → simple.txt (not simple.txt.j2)
        assert (target / "simple.txt").exists()
        assert not (target / "simple.txt.j2").exists()
        # nested/hello.txt.j2 → nested/hello.txt
        assert (target / "nested" / "hello.txt").exists()


# ---------------------------------------------------------------------------
# Non-.j2 files
# ---------------------------------------------------------------------------


def test_non_j2_file_copied_verbatim() -> None:
    """1.2.C — Files without .j2 extension are copied verbatim."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project({}, target)

        output = target / "copy_me.txt"
        assert output.exists()
        content = output.read_text()
        assert "no .j2 extension" in content
        assert "{{" not in content  # not processed by Jinja2


# ---------------------------------------------------------------------------
# Target directory creation
# ---------------------------------------------------------------------------


def test_target_dir_created_if_not_exists() -> None:
    """render_project creates target_dir if it doesn't exist."""
    renderer = Renderer(FIXTURE_TEMPLATES)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "new_subdir" / "project"
        assert not target.exists()
        renderer.render_project({"name": "X"}, target)
        assert target.exists()
        assert (target / "simple.txt").exists()


# ---------------------------------------------------------------------------
# Real project templates — syntactic validity
# ---------------------------------------------------------------------------


@pytest.fixture
def project_renderer() -> Renderer:
    return Renderer(PROJECT_TEMPLATES)


@pytest.fixture
def pure_context() -> dict:
    return dict(MINIMAL_CONTEXT)


def assert_valid_python(source: str, label: str) -> None:
    """Assert that *source* can be parsed as valid Python."""
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"{label} produced invalid Python:\n{e}\n\n{source}")


def assert_valid_toml(source: str, label: str) -> None:
    """Assert that *source* can be parsed as valid TOML (basic check)."""
    try:
        import tomllib as _toml
    except ImportError:
        import tomli as _toml  # type: ignore[no-redef]
    try:
        _toml.loads(source)
    except Exception as e:
        pytest.fail(f"{label} produced invalid TOML:\n{e}\n\n{source}")


def test_pyproject_toml_template(project_renderer: Renderer, pure_context: dict) -> None:
    """1.2.D — pyproject.toml.j2 produces valid TOML."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "pyproject.toml"
        assert output.exists()
        assert_valid_toml(output.read_text(), "pyproject.toml")


def test_settings_base_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.2.E — config/settings/base.py.j2 produces valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "config" / "settings" / "base.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "config/settings/base.py")


def test_urls_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.2.F — config/urls.py.j2 produces valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "config" / "urls.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "config/urls.py")


def test_asgi_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """config/asgi.py.j2 produces valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "config" / "asgi.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "config/asgi.py")


def test_wsgi_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """config/wsgi.py.j2 produces valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "config" / "wsgi.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "config/wsgi.py")


def test_manage_py_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.2.G — manage.py.j2 produces valid Python with correct shebang."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "manage.py"
        assert output.exists()
        content = output.read_text()
        assert content.startswith("#!/usr/bin/env python")
        assert "DJANGO_SETTINGS_MODULE" in content
        assert_valid_python(content, "manage.py")


def test_accounts_apps_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """apps/accounts/apps.py.j2 produces valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "apps.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "apps/accounts/apps.py")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Tooling template tests (Story 1.4)
# ---------------------------------------------------------------------------


def test_pyproject_toml_has_dev_deps(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.A — pyproject.toml has [project.optional-dependencies] dev section."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        content = (target / "pyproject.toml").read_text()
        assert "[project.optional-dependencies]" in content
        assert "ruff>=" in content
        assert "ty>=" in content
        assert "pytest>=" in content
        assert "pytest-django>=" in content
        assert "factory-boy>=" in content
        assert "coverage>=" in content


def test_pyproject_toml_has_ruff_config(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.B-C — pyproject.toml has [tool.ruff] and [tool.ruff.format]."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        content = (target / "pyproject.toml").read_text()
        assert "[tool.ruff]" in content
        assert "line-length = 100" in content
        assert 'target-version = "py312"' in content
        assert "[tool.ruff.lint]" in content
        assert "[tool.ruff.format]" in content
        assert 'quote-style = "double"' in content


def test_pyproject_toml_has_ty_config(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.D — pyproject.toml has [tool.ty] section."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        content = (target / "pyproject.toml").read_text()
        assert "[tool.ty]" in content
        assert 'python-version = "3.12"' in content


def test_pyproject_toml_has_pytest_config(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.E — pyproject.toml has [tool.pytest.ini_options] with DJANGO_SETTINGS_MODULE."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        content = (target / "pyproject.toml").read_text()
        assert "[tool.pytest.ini_options]" in content
        assert 'minversion = "8.0"' in content
        assert 'testpaths = ["tests"]' in content
        assert "DJANGO_SETTINGS_MODULE" in content


def test_ci_workflow_valid_yaml(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.F — .github/workflows/ci.yml is valid YAML."""
    import yaml as _yaml

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / ".github" / "workflows" / "ci.yml"
        assert output.exists()
        _yaml.safe_load(output.read_text())


def test_pre_commit_config_valid_yaml(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.H — .pre-commit-config.yaml is valid YAML."""
    import yaml as _yaml

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / ".pre-commit-config.yaml"
        assert output.exists()
        _yaml.safe_load(output.read_text())


def test_conftest_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.I — tests/conftest.py renders to valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "tests" / "conftest.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "tests/conftest.py")


def test_example_test_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.J — tests/test_example.py renders to valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "tests" / "test_example.py"
        assert output.exists()
        assert_valid_python(output.read_text(), "tests/test_example.py")


def test_makefile_uses_uv(project_renderer: Renderer, pure_context: dict) -> None:
    """1.4.N — Makefile uses uv run for all commands."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "Makefile"
        assert output.exists()
        content = output.read_text()
        assert "uv run" in content
        assert "pip" not in content


# ---------------------------------------------------------------------------
# Auth template tests (Story 1.5)
# ---------------------------------------------------------------------------


def test_auth_models_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.A — models.py renders to valid Python with AbstractUser."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "models.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/models.py")
        assert "AbstractUser" in src
        assert 'USERNAME_FIELD = "email"' in src
        assert "email" in src  # email field exists


def test_auth_models_has_usermanager(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.I — models.py references UserManager from managers.py."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        src = (target / "apps" / "accounts" / "models.py").read_text()
        assert "objects = UserManager()" in src


def test_auth_managers_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.B — managers.py renders to valid Python with UserManager."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "managers.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/managers.py")
        assert "create_user" in src
        assert "create_superuser" in src


def test_auth_admin_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.C — admin.py renders to valid Python with custom UserAdmin."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "admin.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/admin.py")
        assert "UserAdmin" in src
        assert "UserCreationForm" in src
        assert "UserChangeForm" in src


def test_auth_forms_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.D — forms.py renders to valid Python with UserCreationForm."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "forms.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/forms.py")
        assert "UserCreationForm" in src
        assert "UserChangeForm" in src


def test_auth_urls_python_valid_pure(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.L — urls.py for pure Django renders valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "urls.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/urls.py")
        assert "LoginView" in src  # pure Django uses LoginView


def test_auth_urls_python_valid_drf() -> None:
    """1.5.K — urls.py for DRF context renders valid Python with viewset."""
    renderer = Renderer(PROJECT_TEMPLATES)
    ctx = {
        "project_name": "testproj",
        "project_slug": "testproj",
        "secret_key": "key",
        "api": "drf",
        "db": "sqlite",
        "layers": [],
        "use_drf": True,
        "use_ninja": False,
        "use_pure_django": False,
        "has_docker": False,
        "has_celery": False,
        "has_email": False,
    }
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer.render_project(ctx, target)
        output = target / "apps" / "accounts" / "urls.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/urls.py (DRF)")
        assert "ModelViewSet" in src
        assert "DefaultRouter" in src


def test_auth_signals_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.F — signals.py renders to valid Python with post_save handler."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "signals.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/signals.py")
        assert "post_save" in src
        assert "receiver" in src


def test_auth_apps_has_ready(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.N — apps.py has ready() method importing signals."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        src = (target / "apps" / "accounts" / "apps.py").read_text()
        assert "def ready" in src
        assert "signals" in src


def test_auth_test_models_python_valid(project_renderer: Renderer, pure_context: dict) -> None:
    """1.5.M — tests/test_models.py renders to valid Python."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / "apps" / "accounts" / "tests" / "test_models.py"
        assert output.exists()
        src = output.read_text()
        assert_valid_python(src, "apps/accounts/tests/test_models.py")
        assert "create_user" in src
        assert "create_superuser" in src
        assert "pytest.mark.django_db" in src


# All templates render without UndefinedError
# ---------------------------------------------------------------------------


def test_all_templates_render_with_minimal_context(
    project_renderer: Renderer, pure_context: dict
) -> None:
    """1.2.H — All .j2 templates render without UndefinedError with minimal context."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)


# ---------------------------------------------------------------------------
# Rendered file structure
# ---------------------------------------------------------------------------


def test_rendered_file_structure(project_renderer: Renderer, pure_context: dict) -> None:
    """1.2.I — After rendering, target directory contains all expected files."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)

        expected = [
            "manage.py",
            "pyproject.toml",
            ".env.example",
            ".gitignore",
            "Makefile",
            ".pre-commit-config.yaml",
            ".github/workflows/ci.yml",
            "config/__init__.py",
            "config/settings/__init__.py",
            "config/settings/base.py",
            "config/urls.py",
            "config/asgi.py",
            "config/wsgi.py",
            "apps/__init__.py",
            "apps/accounts/__init__.py",
            "apps/accounts/apps.py",
            "apps/accounts/models.py",
            "apps/accounts/managers.py",
            "apps/accounts/admin.py",
            "apps/accounts/forms.py",
            "apps/accounts/urls.py",
            "apps/accounts/signals.py",
            "apps/accounts/tests/__init__.py",
            "apps/accounts/tests/test_models.py",
            "apps/accounts/views.py",
            "apps/accounts/api.py",
            "templates/base.html",
            "README.md",
            "static/.gitkeep",
            "media/.gitkeep",
            "tests/__init__.py",
            "tests/conftest.py",
            "tests/test_example.py",
            ".forge.toml",
        ]
        for rel_path in expected:
            file_path = target / rel_path
            assert file_path.exists(), f"Expected {rel_path} to exist but it was not created"


# ---------------------------------------------------------------------------
# Forge.toml
# ---------------------------------------------------------------------------


def test_forge_toml_valid_toml(project_renderer: Renderer, pure_context: dict) -> None:
    """1.2.N — .forge.toml is valid TOML with [forge] section."""
    try:
        import tomllib as _toml
    except ImportError:
        import tomli as _toml  # type: ignore[no-redef]

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / ".forge.toml"
        assert output.exists()
        data = _toml.loads(output.read_text())
        assert "forge" in data
        assert data["forge"]["version"] == _forge_version
        assert data["forge"]["api"] == "pure"
        assert data["forge"]["db"] == "sqlite"
        assert data["forge"]["layers"] == []


# ---------------------------------------------------------------------------
# Package-level export
# ---------------------------------------------------------------------------


def test_renderer_exported() -> None:
    """1.2.K — Renderer is exported at package level."""
    from django_forge import Renderer as ForgeRenderer
    from django_forge.renderer import Renderer

    assert ForgeRenderer is Renderer


# ---------------------------------------------------------------------------
# Empty .env.example and .gitignore are valid UTF-8
# ---------------------------------------------------------------------------


def test_env_example_is_valid_utf8(project_renderer: Renderer, pure_context: dict) -> None:
    """.env.example.j2 renders to valid UTF-8 text."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        project_renderer.render_project(pure_context, target)
        output = target / ".env.example"
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "DJANGO_SECRET_KEY" in content
        assert "DJANGO_DEBUG" in content
