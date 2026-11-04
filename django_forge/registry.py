"""Single registry of the eleven optional scaffold layers.

Data only: this module has no export/serialization side effects (the site's
``forge-data.js`` stays hand-written, per the file 7 decision) and it never
imports from ``django_forge.cli`` — handlers are stored as dotted strings so
the CLI can import the registry without a cycle.

Field sources:
* ``label`` / ``description`` — ``django_forge/cli/list_cmd.py``
  (``_print_optional_layers``).
* ``menu_key`` — the numeric menu key each layer has in
  ``django_forge/cli/prompts.py`` (``_LAYERS`` / ``_LAYER_KEY_MAP``).
* ``slug`` — the layer id used on the command line
  (``forge-django add <slug>``); identical to ``id`` today.
* ``rendered_files`` — the per-layer ``modified`` lists of the ``_add_*``
  handlers in ``django_forge/cli/add.py``, as repo-relative paths. Those
  lists are the overwrite-confirmation set; entries the handler appends
  conditionally are marked inline.
* ``dependencies`` — the requirement strings gated on this layer's ``has_*``
  flag in ``django_forge/templates/pyproject.toml.j2``; empty when the layer
  contributes no runtime dependency.
* ``has_flag`` — the render-context key built by
  ``django_forge/cli/prompts.py::_build_context``.
* ``handler`` — the ``module:function`` string dispatched by
  ``django_forge/cli/add.py::add_layer``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    """One optional scaffold layer. Immutable by design."""

    id: str
    label: str
    slug: str
    menu_key: str
    description: str
    rendered_files: tuple[str, ...]
    dependencies: tuple[str, ...]
    has_flag: str
    handler: str


LAYERS: tuple[Layer, ...] = (
    Layer(
        id="docker",
        label="Docker",
        slug="docker",
        menu_key="1",
        description="Multi-stage Dockerfile + Docker Compose (PostgreSQL, app)",
        rendered_files=(
            "Dockerfile",
            "compose.yaml",
            ".dockerignore",
        ),
        dependencies=("gunicorn>=23,<27",),
        has_flag="has_docker",
        handler="django_forge.cli.add:_add_docker",
    ),
    Layer(
        id="celery",
        label="Celery",
        slug="celery",
        menu_key="2",
        description="Background task queue (requires Redis)",
        rendered_files=(
            "config/settings/base.py",
            "config/__init__.py",
            "pyproject.toml",
            "compose.yaml",  # only when the docker layer is present
        ),
        dependencies=(
            "celery~=5.6.0",
            "redis>=5.0,<9.0",
        ),
        has_flag="has_celery",
        handler="django_forge.cli.add:_add_celery",
    ),
    Layer(
        id="email",
        label="Email",
        slug="email",
        menu_key="3",
        description="Mailpit (dev) / SMTP (prod) configuration",
        rendered_files=(
            "config/settings/base.py",
            "config/settings/dev.py",
            "config/settings/prod.py",
            ".env.example",
            "compose.yaml",  # only when the docker layer is present
        ),
        dependencies=(),
        has_flag="has_email",
        handler="django_forge.cli.add:_add_email",
    ),
    Layer(
        id="cache",
        label="Caching",
        slug="cache",
        menu_key="4",
        description="Redis cache backend (django.core.cache.backends.redis)",
        rendered_files=(
            "config/settings/base.py",
            "pyproject.toml",
            "compose.yaml",  # only when docker is present and celery is not
        ),
        dependencies=("redis>=5.0,<9.0",),
        has_flag="has_cache",
        handler="django_forge.cli.add:_add_cache",
    ),
    Layer(
        id="social",
        label="Social Auth",
        slug="social",
        menu_key="5",
        description="Google + GitHub OAuth via django-allauth",
        rendered_files=(
            "config/settings/base.py",
            ".env.example",
        ),
        dependencies=(),
        has_flag="has_social",
        handler="django_forge.cli.add:_add_social",
    ),
    Layer(
        id="storage",
        label="S3 Storage",
        slug="storage",
        menu_key="6",
        description="django-storages[s3] — static + media files on S3/MinIO",
        rendered_files=(
            "config/settings/base.py",
            "config/settings/prod.py",
            "pyproject.toml",
            ".env.example",
        ),
        dependencies=("django-storages[s3]>=1.14,<2.0",),
        has_flag="has_storage",
        handler="django_forge.cli.add:_add_storage",
    ),
    Layer(
        id="healthcheck",
        label="Health Check",
        slug="healthcheck",
        menu_key="7",
        description="django-health-check — /healthz for load balancers",
        rendered_files=(
            "config/settings/base.py",
            "config/urls.py",
            "pyproject.toml",
        ),
        dependencies=("django-health-check>=4.6,<5",),
        has_flag="has_healthcheck",
        handler="django_forge.cli.add:_add_healthcheck",
    ),
    Layer(
        id="audit",
        label="Audit Trail",
        slug="audit",
        menu_key="8",
        description="django-simple-history — record every model change",
        rendered_files=(
            "apps/accounts/models.py",
            "apps/accounts/admin.py",
            "config/settings/base.py",
            "pyproject.toml",
        ),
        dependencies=("django-simple-history>=3.7,<4.0",),
        has_flag="has_audit",
        handler="django_forge.cli.add:_add_audit",
    ),
    Layer(
        id="backup",
        label="Backup",
        slug="backup",
        menu_key="9",
        description="django-dbbackup — nightly DB dumps + restore drill",
        rendered_files=(
            "config/settings/base.py",
            "pyproject.toml",
            "Makefile",
            "README.md",
        ),
        dependencies=("django-dbbackup>=4.2,<6",),
        has_flag="has_backup",
        handler="django_forge.cli.add:_add_backup",
    ),
    Layer(
        id="seed",
        label="Seed Data",
        slug="seed",
        menu_key="10",
        description="factory-boy dev data + manage.py seed command",
        rendered_files=("Makefile",),
        dependencies=(),
        has_flag="has_seed",
        handler="django_forge.cli.add:_add_seed",
    ),
    Layer(
        id="preflight",
        label="Preflight",
        slug="preflight",
        menu_key="11",
        description="manage.py preflight — deploy check before pushing",
        rendered_files=("Makefile",),
        dependencies=(),
        has_flag="has_preflight",
        handler="django_forge.cli.add:_add_preflight",
    ),
)
