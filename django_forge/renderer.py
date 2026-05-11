"""Jinja2 template rendering engine for project scaffolding."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class Renderer:
    """Renders Jinja2 templates into a target project directory.

    Loads templates from a root directory, renders them with a context dict,
    and writes the output to a target directory. Files with a ``.j2`` extension
    are processed through Jinja2 (the ``.j2`` suffix is stripped in the output).
    All other files are copied verbatim.
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

    def render_project(
        self,
        context: dict,
        target_dir: Path,
    ) -> list[tuple[Path, int]]:
        """Render all templates into *target_dir*.

        Iterates over every file in the template root. ``.j2`` files are rendered
        through Jinja2 with *context* and written to *target_dir* with the
        ``.j2`` suffix stripped. Non-``.j2`` files are copied verbatim.

        Args:
            context: Template variables (see architecture.md §3.3).
            target_dir: Output directory. Created if it does not exist.

        Returns:
            List of ``(relative_path, byte_count)`` tuples for every file
            written, ordered by path. Suitable for progress reporting.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        written: list[tuple[Path, int]] = []

        for template_path in sorted(self.template_root.rglob("*")):
            if not template_path.is_file():
                continue

            rel_path = template_path.relative_to(self.template_root)
            output_name = self._output_name(rel_path)
            output_path = target_dir / output_name

            output_path.parent.mkdir(parents=True, exist_ok=True)

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

            output_path.write_text(rendered, encoding="utf-8")
            written.append((output_name, len(rendered.encode("utf-8"))))

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
