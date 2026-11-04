## Checklist

- [ ] Local gates pass: `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check django_forge tests`, `uv run pytest`
- [ ] Site gate passes when `site/` is touched: `cd site && npm ci && npm run check`
- [ ] Generated output unchanged, or tests updated to match the change
- [ ] `CHANGELOG.md` entry added for user-facing changes
