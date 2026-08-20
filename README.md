# famille-busson

Private family website for the Busson family: a member directory (`annuaire`) with
family relations, chalet listings, PSV presence scheduling and a map of member
locations, and a small blog (`publications`) for posts, comments and attachments. Django
6 / Python 3.13, deployed continuously to a single VPS.

## Quickstart

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py populate_dev_data   # seeds dev fixtures + test credentials
uv run python manage.py runserver
```

See [`docs/`](docs/) for the data model, roadmap archive and deployment reference, and
`.claude/skills/dev-commands/SKILL.md` for the full list of dev commands (test
credentials included).

## Documentation

- [`docs/data_model.md`](docs/data_model.md) — data model (ER diagram + field tables),
  auto-generated from `models.py`.
- [`docs/deployment.md`](docs/deployment.md) — how this ships to production.
- [`docs/permissions.md`](docs/permissions.md) — who can do what: the mixins/`get_object()`
  overrides that gate each view.
- [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) — shipped roadmap items.
- [`ROADMAP.md`](ROADMAP.md) — pending work.

Published at https://reboulip.github.io/famille-busson/ on every push to `main`.
