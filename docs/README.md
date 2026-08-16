# Documentation

- [`data_model.md`](data_model.md) — data model reference (entity-relationship diagram +
  per-model field tables). **Auto-generated, do not edit by hand** — regenerate with:
  ```
  uv run python manage.py generate_data_model_docs
  ```
  after any change to `annuaire/models.py` or `publications/models.py`. The generator
  lives in `annuaire/management/commands/generate_data_model_docs.py`.
- [`ROADMAP_ARCHIVE.md`](ROADMAP_ARCHIVE.md) — history of roadmap items already shipped
  to production. Items are moved here from `ROADMAP.md` at release time (see
  `release-workflow`) so `ROADMAP.md` only ever shows pending work.

## Suggested next step: keep `data_model.md` from going stale

Nothing currently forces a regeneration when `models.py` changes — it's a manual step.
Worth considering once this drifts in practice:
- A CI check on `tests.yml` that reruns the generator and fails the build if
  `docs/data_model.md` differs from the committed version (`git diff --exit-code`).
- Or a pre-commit hook that regenerates it automatically when `models.py` is staged.

Not wired up yet — ask if you want either added.
