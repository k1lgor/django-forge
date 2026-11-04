"""Registry consistency and the pre-Stage-3 behaviour guard (design entry 46).

Asserts that the registry, the templates' ``has_*`` flags, the site's
hand-written ``forge-data.js`` and the README layer table all describe the
same eleven layers, and that ``detect_project`` / ``build_context`` still
produce exactly the output captured before the Stage 3 consumer switch
(behaviour-preserving refactor guard).
"""

import importlib
import json
import re
import tempfile
from pathlib import Path

import pytest

from django_forge.project import build_context, detect_project
from django_forge.registry import LAYERS

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
TEMPLATE_ROOT = ROOT / "django_forge" / "templates"
IDS = [layer.id for layer in LAYERS]
LABELS = [layer.label for layer in LAYERS]


def test_registry_has_the_eleven_layers() -> None:
    """Eleven unique layers, ordered menu keys 1..11, slug == id."""
    assert len(LAYERS) == 11
    assert len(set(IDS)) == 11
    assert [layer.menu_key for layer in LAYERS] == [str(n) for n in range(1, 12)]
    for layer in LAYERS:
        assert layer.slug == layer.id
        assert layer.has_flag == f"has_{layer.id}"
        assert layer.label and layer.description
        assert layer.rendered_files


def test_registry_handlers_resolve() -> None:
    """Every dotted handler string imports to a callable."""
    for layer in LAYERS:
        module_name, _, func_name = layer.handler.partition(":")
        module = importlib.import_module(module_name)
        assert callable(getattr(module, func_name)), layer.handler


def test_templates_use_exactly_the_registry_flags() -> None:
    """The template tree branches on exactly the registry's has_* flags."""
    used: set[str] = set()
    for path in TEMPLATE_ROOT.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            used.update(re.findall(r"has_[a-z_]+", text))
    assert used == {layer.has_flag for layer in LAYERS}


def test_site_layers_match_registry() -> None:
    """forge-data.js LAYERS ids and names agree with the registry."""
    js_path = ROOT / "site" / "src" / "lib" / "forge-data.js"
    if not js_path.exists():  # site/ is not shipped in the sdist
        pytest.skip("site/ not shipped in the sdist")  # ty: ignore
    js = js_path.read_text(encoding="utf-8")
    section = js.split("export const LAYERS = [", 1)[1].split("];", 1)[0]
    site_ids = re.findall(r'id: "([a-z_]+)"', section)
    site_names = re.findall(r'name: "([^"]+)"', section)
    assert len(site_ids) == 11
    assert set(site_ids) == set(IDS)
    assert set(site_names) == set(LABELS)


def test_readme_layer_table_matches_registry() -> None:
    """The README optional-layers table carries exactly the registry labels."""
    md = (ROOT / "README.md").read_text(encoding="utf-8")
    section = md.split("## Optional layers (all 11)", 1)[1].split("\n## ", 1)[0]
    labels = re.findall(r"^\| \*\*(.+?)\*\* \|", section, flags=re.MULTILINE)
    assert len(labels) == 11
    assert set(labels) == set(LABELS)


def test_build_context_matches_pre_stage3_fixtures() -> None:
    """build_context output is byte-identical to the captured baseline."""
    payload = json.loads((FIXTURES / "build_context_cases.json").read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert len(cases) == 3
    for case in cases:
        assert build_context(dict(case["state"])) == case["context"]


def test_detect_project_matches_pre_stage3_fixture() -> None:
    """detect_project output is identical to the captured baseline."""
    payload = json.loads((FIXTURES / "detect_project_case.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "detected-project"
        root.mkdir()
        (root / ".forge.toml").write_text(payload["toml"], encoding="utf-8")
        (root / "manage.py").write_text("# manage.py\n", encoding="utf-8")
        state = detect_project(root)
    assert state == payload["state"]
