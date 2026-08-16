# Documentation

Published at https://reboulip.github.io/famille-busson/ on every push to `main` (via
`.github/workflows/docs.yml` + `mkdocs.yml`).

- [`data_model.md`](data_model.md) — data model reference (entity-relationship diagram +
  per-model field tables). **Auto-generated, do not edit by hand** — a pre-commit hook
  (`.pre-commit-config.yaml`) regenerates it automatically whenever
  `annuaire/models.py` or `publications/models.py` changes. Manual run:
  `uv run python manage.py generate_data_model_docs`. Generator source:
  `annuaire/management/commands/generate_data_model_docs.py`.
- [`deployment.md`](deployment.md) — how the app ships to production (Docker image, VPS
  layout, CI/CD workflows, environment variables).
- [`permissions.md`](permissions.md) — who can do what: the mixins/`get_object()`
  overrides that gate each view, by view.
- [`ROADMAP_ARCHIVE.md`](ROADMAP_ARCHIVE.md) — history of roadmap items already shipped
  to production. Items are moved here from `ROADMAP.md` at release time (see
  `release-workflow`) so `ROADMAP.md` only ever shows pending work.
