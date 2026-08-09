"""Jinja2 template rendering engine for project scaffolding."""

import contextlib
import hashlib
import json
import os
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

MANIFEST_NAME = ".forge-manifest.json"


class Renderer:
    """Renders Jinja2 templates into a target project directory.

    Loads templates from a root directory, renders them with a context dict,
    and writes the output to a target directory. Files with a ``.j2`` extension
    are processed through Jinja2 (the ``.j2`` suffix is stripped in the output).
    All other files are copied verbatim.

    Every render records a manifest (``.forge-manifest.json``) in the target
    directory mapping each written file to the sha256 of the bytes forge last
    wrote. Re-renders with ``policy="pristine"`` use that manifest to leave
    user-edited or user-created files untouched.
    """

    def __init__(self, template_root: Path) -> None:
        """Initialize with the path to the template directory.

        Args:
            template_root: Directory containing the template tree.
                All files within (recursively) are candidates for rendering.

        Raises:
            FileNotFoundError: If *template_root* does not exist.
        """
        if not template_root.exists():
            raise FileNotFoundError(f"Template root not found: {template_root}")
        self.template_root = template_root
        self._env = Environment(
            loader=FileSystemLoader(str(template_root)),
            autoescape=False,
            keep_trailing_newline=True,
        )
        # Files skipped by policy="pristine" during the last render call.
        self.skipped: list[tuple[Path, str]] = []

    def render_project(
        self,
        context: dict,
        target_dir: Path,
        *,
        policy: str = "overwrite",
    ) -> list[tuple[Path, int]]:
        """Render all templates into *target_dir*.

        Iterates over every file in the template root. ``.j2`` files are rendered
        through Jinja2 with *context* and written to *target_dir* with the
        ``.j2`` suffix stripped. Non-``.j2`` files are copied verbatim.

        Args:
            context: Template variables (see architecture.md §3.3).
            target_dir: Output directory. Created if it does not exist.
            policy: ``"overwrite"`` always writes; ``"pristine"`` skips files
                that exist and differ from the last-render manifest (i.e. files
                the user has edited or created), leaving them untouched.

        Returns:
            List of ``(relative_path, byte_count)`` tuples for every file
            written, ordered by path. Suitable for progress reporting.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_root = target_dir.resolve()

        # Imported lazily to avoid a circular import with django_forge/__init__.
        from django_forge import __version__ as forge_version

        self.skipped = []
        manifest = _read_manifest(target_dir)
        files = dict(manifest.get("files", {})) if manifest else {}
        written: list[tuple[Path, int]] = []
        template_sha = _template_tree_sha(self.template_root)

        for template_path in sorted(self.template_root.rglob("*")):
            if not template_path.is_file():
                continue

            rel_path = template_path.relative_to(self.template_root)
            output_name = self._output_name(rel_path)
            output_path = target_dir / output_name

            # Never write through a symlink that escapes the project root.
            if not output_path.resolve().is_relative_to(target_root):
                raise RuntimeError(
                    f"Refusing to write {output_name}: resolves outside "
                    f"the project directory ({target_root})"
                )

            if rel_path.suffix == ".j2":
                template = self._env.get_template(str(rel_path.as_posix()))
                rendered = template.render(**context)
            else:
                rendered = template_path.read_text(encoding="utf-8")

            # Skip files that rendered to empty due to Jinja2 conditionals.
            # If the template itself had content (like {% if has_docker %}) but
            # rendered to empty, the conditional was false — skip the file.
            # If the template was already empty (like __init__.py.j2), keep it.
            if not rendered.strip():
                template_source = template_path.read_text(encoding="utf-8")
                if template_source.strip():
                    continue

            key = output_name.as_posix()
            if policy == "pristine" and manifest is not None and output_path.exists():
                previous = manifest.get("files", {}).get(key)
                if previous is None or _sha256_file(output_path) != previous:
                    self.skipped.append((output_name, "user-modified"))
                    continue

            _atomic_write_text(output_path, rendered)
            written.append((output_name, len(rendered.encode("utf-8"))))
            files[key] = _sha256_bytes(rendered.encode("utf-8"))

        if written:
            _write_manifest(target_dir, template_sha, files, forge_version)

        return written

    @staticmethod
    def _output_name(rel_path: Path) -> Path:
        """Strip the ``.j2`` suffix from a template path, preserving
        the parent directory structure and any other extensions.

        Examples::
            Path("base.py.j2")         → Path("base.py")
            Path("nested/hello.txt.j2") → Path("nested/hello.txt")
            Path("copy_me.txt")         → Path("copy_me.txt")
        """
        if rel_path.suffix == ".j2":
            parent = rel_path.parent
            stem_without_j2 = rel_path.stem
            return parent / stem_without_j2
        return rel_path


def _atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically (temp file in same dir + os.replace).

    Writes raw UTF-8 bytes so the bytes on disk always match the bytes the
    manifest hashes — no platform newline translation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _template_tree_sha(template_root: Path) -> str:
    """Hash of the template tree: relative paths + contents, sorted."""
    digest = hashlib.sha256()
    for path in sorted(template_root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(template_root).as_posix()
            digest.update(rel.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _read_manifest(project_dir: Path) -> dict | None:
    """Load the render manifest, or ``None`` if missing or unreadable."""
    manifest_path = project_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _write_manifest(
    project_dir: Path,
    template_sha: str,
    files: dict[str, str],
    forge_version: str,
) -> None:
    """Atomically write the render manifest for *project_dir*."""
    payload = {
        "forge_version": forge_version,
        "template_sha": template_sha,
        "files": dict(sorted(files.items())),
    }
    _atomic_write_text(
        project_dir / MANIFEST_NAME,
        json.dumps(payload, indent=2) + "\n",
    )
