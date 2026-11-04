# Contributing to django-forge

Thanks for contributing. This document is the development loop: setup, gates,
and the two workflows that keep the registry, the templates, the README and
the landing page in agreement.

The distribution and the console script are both named `forge-django`. Use
`forge-django` in docs, tests and examples — never bare `forge`.

## Development setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Python 3.10+, and Node.js
with npm (only for work under `site/`).

```bash
git clone https://github.com/k1lgor/django-forge.git
cd django-forge
uv sync        # installs the project plus dev tooling from [dependency-groups] dev
```

Dev tooling (ruff, ty, pytest and the template test dependencies) lives in
`[dependency-groups] dev` in `pyproject.toml`, which plain `uv sync` installs
by default — no extra flags. uv manages the virtualenv; all commands below run
through `uv run`.

## Gates

Every gate must pass locally before a PR is opened; CI runs the same commands.

```bash
uv run ruff check .                 # lint
uv run ruff format --check .        # formatting
uv run ty check django_forge tests  # type check (tests are in scope)
uv run pytest                       # test suite — 448 tests
```

Site gate — required whenever `site/` is touched:

```bash
cd site && npm ci && npm run check  # svelte-check --fail-on-warnings
```

CI (`.github/workflows/ci.yml`) runs lint + typecheck, install checks and the
test suite on Python 3.10–3.14 across Ubuntu, macOS and Windows; an
`e2e-scaffold` matrix (framework × database × Python 3.12/3.14) that scaffolds
a real project and runs the generated project's own `make lint` /
`make typecheck` / `make test` plus its deploy check; a `package` job
(`uv build`, `twine check`, a wheel-content assertion and pytest from the
unpacked sdist); and a `site` job (`npm ci && npm run check`).

## Adding a layer

`django_forge/registry.py` is the single source of truth. Each layer is one
`Layer(id, label, slug, menu_key, description, rendered_files, dependencies,
has_flag, handler)` entry in `LAYERS`. The wizard menu
(`django_forge/cli/prompts.py`) and `forge-django list`
(`django_forge/cli/list_cmd.py`) derive from the registry automatically — do
not hand-edit them.

1. Add the `Layer` entry to `LAYERS` in `django_forge/registry.py`.
2. Add templates under `django_forge/templates/` that branch on its
   `has_flag`. The `has_*` context flags are written from the registry by
   `build_context` in `django_forge/project.py`; the registry entry drives
   them, so keep the template branches in step with it.
3. Implement the handler named in `handler` — a dotted string of the form
   `django_forge.cli.add:_add_<layer>` — in `django_forge/cli/add.py`.
   Dispatch resolves the function through the registry.
4. Add a row to the optional-layers table in `README.md`.
5. Add the layer to the `LAYERS` array in `site/src/lib/forge-data.js`. This
   file is hand-written by design — there is no export artifact — so the edit
   is manual.
6. Verify:

   ```bash
   uv run pytest tests/test_parity.py tests/test_registry.py
   ```

   These assert that the registry, the templates' `has_*` flags,
   `site/src/lib/forge-data.js` and the README table all agree (eleven layers
   today).

## Changing dependency pins

A pin change (django, celery, and friends) lands in three places:

1. `django_forge/templates/pyproject.toml.j2` — what generated projects get.
2. `site/src/lib/forge-data.js` — the pins shown on the landing page.
3. `README.md` — the documented pins.

Run the parity and registry tests afterwards; they catch drift between these
artifacts.

## Parity tests

- `tests/test_parity.py` asserts that the distribution name, the install
  command, the repository URL and the version agree across
  `pyproject.toml`, `django_forge.__version__`, `README.md`, `site/index.html`,
  `site/src/lib/forge-data.js` and the generated templates.
- `tests/test_registry.py` asserts the registry itself: layer count, handler
  resolution, template flags, the site `LAYERS` ids and the README table.

Run them after any change to layers, pins, naming or release metadata:

```bash
uv run pytest tests/test_parity.py tests/test_registry.py
```

## Pull requests

- Keep changes scoped; open an issue first for anything that changes generated
  output or the public command surface.
- Run all gates above; CI must be green.
- Generated output must stay unchanged, or the tests that pin it must be
  updated in the same commit.
- Add a `CHANGELOG.md` entry for user-facing changes (Keep a Changelog format,
  under the current unreleased version).

## Reporting security issues

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately through
GitHub Security Advisories — never in a public issue.
