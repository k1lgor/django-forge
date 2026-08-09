"""Regression tests for the hardening pass:

- ownership manifest + pristine re-render policy
- project-name validation and --no-input refusal
- secret preservation across forge add / forge upgrade
- generated-project template fixes (prod security, gunicorn, .env, auth URLs)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from django_forge import __version__ as _forge_version
from django_forge.cli.add import _update_forge_toml
from django_forge.cli.main import app
from django_forge.cli.start import validate_project_name
from django_forge.renderer import MANIFEST_NAME, Renderer

runner = CliRunner()
_PATCH_PATH = "django_forge.cli.start.run_post_install"

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
    "has_cache": False,
    "has_social": False,
    "has_storage": False,
    "forge_version": _forge_version,
}


def _render(ctx: dict, target: Path, policy: str = "overwrite") -> Renderer:
    renderer = Renderer(PROJECT_TEMPLATES)
    renderer.render_project(ctx, target, policy=policy)
    return renderer


# ---------------------------------------------------------------------------
# Ownership manifest
# ---------------------------------------------------------------------------


def test_render_writes_manifest() -> None:
    """A render writes .forge-manifest.json with per-file hashes."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)
        manifest_path = target / MANIFEST_NAME
        assert manifest_path.exists()
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["forge_version"] == _forge_version
        assert "template_sha" in manifest
        files = manifest["files"]
        assert "config/settings/base.py" in files
        expected = (target / "config" / "settings" / "base.py").read_bytes()
        assert files["config/settings/base.py"] == _sha256(expected)


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def test_pristine_policy_skips_user_edited_files() -> None:
    """policy='pristine' leaves user-edited files untouched and reports them."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        renderer = _render(dict(MINIMAL_CONTEXT), target)

        base_py = target / "config" / "settings" / "base.py"
        base_py.write_text(base_py.read_text() + "\n# USER EDIT\n")

        renderer.render_project(dict(MINIMAL_CONTEXT), target, policy="pristine")
        assert "# USER EDIT" in base_py.read_text()
        assert any(
            p.as_posix() == "config/settings/base.py" and reason == "user-modified"
            for p, reason in renderer.skipped
        )


def test_pristine_policy_refreshes_pristine_files() -> None:
    """policy='pristine' refreshes files forge last wrote unchanged."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)

        # Delete a forge-written file — pristine re-render restores it.
        (target / "Makefile").unlink()
        renderer = _render(dict(MINIMAL_CONTEXT), target, policy="pristine")
        assert (target / "Makefile").exists()
        assert renderer.skipped == []


def test_pristine_policy_without_manifest_overwrites() -> None:
    """No manifest (pre-manifest project) degrades to full overwrite."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)
        (target / MANIFEST_NAME).unlink()

        base_py = target / "config" / "settings" / "base.py"
        base_py.write_text(base_py.read_text() + "\n# USER EDIT\n")

        renderer = _render(dict(MINIMAL_CONTEXT), target, policy="pristine")
        assert "# USER EDIT" not in base_py.read_text()
        assert renderer.skipped == []


# ---------------------------------------------------------------------------
# Project name validation
# ---------------------------------------------------------------------------


def test_validate_project_name_accepts_legal_names() -> None:
    for name in ("myproject", "my-project", "my_project", "my.project", "42project"):
        assert validate_project_name(name) is None, name


def test_validate_project_name_rejects_hostile_names() -> None:
    for name in ("../evil", "a/b", "a\\b", ".hidden", "..", "{{x}}", "{%x%}", ""):
        assert validate_project_name(name) is not None, name


@patch(_PATCH_PATH, return_value=True)
def test_start_rejects_path_escape_name(_mock_install, tmp_path: Path) -> None:
    """A hostile project name is refused before anything touches disk."""
    os.chdir(tmp_path)
    result = runner.invoke(app, ["start", "../evil", "--no-input"])
    assert result.exit_code == 0
    assert "Project name" in result.stdout
    assert not (tmp_path.parent / "evil").exists()


@patch(_PATCH_PATH, return_value=True)
def test_no_input_refuses_existing_directory(_mock_install, tmp_path: Path) -> None:
    """--no-input must not silently delete an existing directory."""
    os.chdir(tmp_path)
    (tmp_path / "myapp").mkdir()
    (tmp_path / "myapp" / "keep.txt").write_text("keep")
    result = runner.invoke(app, ["start", "myapp", "--no-input"])
    assert result.exit_code == 0
    assert "Refusing" in result.stdout
    assert (tmp_path / "myapp" / "keep.txt").read_text() == "keep"


# ---------------------------------------------------------------------------
# Secret preservation across add / upgrade
# ---------------------------------------------------------------------------


def _start_project(tmp_path: Path, name: str = "testproj") -> Path:
    os.chdir(tmp_path)
    runner.invoke(app, ["start", name, "--no-input"])
    project = tmp_path / name
    os.chdir(project)
    return project


@patch(_PATCH_PATH, return_value=True)
def test_add_preserves_secret_key(_mock_install, tmp_path: Path) -> None:
    """forge add must not blank the generated SECRET_KEY."""
    project = _start_project(tmp_path)
    runner.invoke(app, ["add", "celery"], input="Y\n")
    base_py = (project / "config" / "settings" / "base.py").read_text()
    assert 'django_secret_key: str = "django-insecure-' in base_py
    assert 'django_secret_key: str = ""' not in base_py


@patch(_PATCH_PATH, return_value=True)
def test_upgrade_preserves_secret_key(_mock_install, tmp_path: Path) -> None:
    """forge upgrade must not blank the generated SECRET_KEY."""
    project = _start_project(tmp_path)
    runner.invoke(app, ["upgrade"], input="Y\n")
    after = (project / "config" / "settings" / "base.py").read_text()
    assert 'django_secret_key: str = "django-insecure-' in after
    assert 'django_secret_key: str = ""' not in after


@patch(_PATCH_PATH, return_value=True)
def test_add_skips_user_edited_settings(_mock_install, tmp_path: Path) -> None:
    """forge add leaves a user-edited settings file byte-identical."""
    project = _start_project(tmp_path)
    base_py = project / "config" / "settings" / "base.py"
    base_py.write_text(base_py.read_text() + "\n# MY CUSTOM SETTING\n")
    runner.invoke(app, ["add", "celery"], input="Y\n")
    assert "# MY CUSTOM SETTING" in base_py.read_text()


# ---------------------------------------------------------------------------
# _update_forge_toml preserves extra sections
# ---------------------------------------------------------------------------


def test_update_forge_toml_preserves_extra_sections(tmp_path: Path) -> None:
    """Extra top-level sections survive a layers update."""
    (tmp_path / ".forge.toml").write_text(
        '[forge]\napi = "drf"\ndb = "postgres"\nlayers = []\n\n'
        '[database]\nurl = "sqlite:///dev.db"\n',
        encoding="utf-8",
    )
    _update_forge_toml(tmp_path / ".forge.toml", ["docker"])
    import tomli

    toml = tomli.loads((tmp_path / ".forge.toml").read_text())
    assert toml["database"]["url"] == "sqlite:///dev.db"
    assert "docker" in toml["forge"]["layers"]


# ---------------------------------------------------------------------------
# Generated-project template fixes
# ---------------------------------------------------------------------------


def test_gunicorn_in_deps_when_docker() -> None:
    """Docker layer adds gunicorn (the Dockerfile CMD depends on it)."""
    ctx = dict(MINIMAL_CONTEXT)
    ctx.update(layers=["docker"], has_docker=True)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(ctx, target)
        toml = (target / "pyproject.toml").read_text()
        assert "gunicorn" in toml


def test_no_gunicorn_without_docker() -> None:
    ctx = dict(MINIMAL_CONTEXT)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(ctx, target)
        assert "gunicorn" not in (target / "pyproject.toml").read_text()


def test_gitignore_ignores_env_file() -> None:
    """.env must be ignored; .env.example must stay tracked."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)
        content = (target / ".gitignore").read_text()
        assert ".env" in content
        assert "!.env.example" in content


def test_prod_allowed_hosts_is_env_driven() -> None:
    """prod.py must not hardcode ALLOWED_HOSTS = ['*']."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)
        prod = (target / "config" / "settings" / "prod.py").read_text()
        assert "ALLOWED_HOSTS = settings.allowed_hosts" in prod
        assert 'ALLOWED_HOSTS = ["*"]' not in prod


def test_pure_urls_profile_is_real_profile_view() -> None:
    """profile/ must map to ProfileView, not PasswordResetView."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)
        urls = (target / "apps" / "accounts" / "urls.py").read_text()
        assert "ProfileView.as_view" in urls
        assert urls.count("PasswordResetView") == 1  # only the real reset view


def test_pure_mode_ships_account_templates() -> None:
    """Pure-mode auth views reference accounts/*.html — they must exist."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(dict(MINIMAL_CONTEXT), target)
        for name in (
            "login.html",
            "signup.html",
            "profile.html",
            "password_reset.html",
            "password_reset_done.html",
            "password_reset_confirm.html",
            "password_reset_complete.html",
        ):
            assert (target / "templates" / "accounts" / name).exists(), name


def test_drf_mode_omits_account_templates() -> None:
    """DRF projects don't need the pure-mode HTML templates."""
    ctx = dict(MINIMAL_CONTEXT)
    ctx.update(api="drf", use_drf=True, use_pure_django=False)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(ctx, target)
        assert not (target / "templates" / "accounts" / "login.html").exists()


def test_compose_sqlite_has_no_db_container() -> None:
    """SQLite projects don't get a useless sqlite container service."""
    ctx = dict(MINIMAL_CONTEXT)
    ctx.update(layers=["docker"], has_docker=True)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        _render(ctx, target)
        compose = (target / "compose.yaml").read_text()
        assert "nouchka/sqlite3" not in compose
        assert "sqlite_data" not in compose
