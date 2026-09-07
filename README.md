# famille-busson

Private family website for the Busson family: a member directory (`annuaire`) with
family relations, an interactive family tree, chalet listings, PSV presence scheduling,
a map of member and chalet locations, site-wide search and an activity feed ("Quoi de
neuf"), a small blog (`publications`) for tagged posts, comments and attachments, a
group-restricted document library (`documents`) for categorized file uploads, and a
group-restricted photo library (`photos`) of albums and photos. Django 6 / Python 3.13,
deployed continuously to a single VPS.

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
- [`docs/design_system.md`](docs/design_system.md) — the Alpenglow/Nightfall design
  system: tokens, components, and the checklist for adding a view.
- [`docs/emails.md`](docs/emails.md) — the five outgoing emails and how to preview them.
- [`docs/permissions.md`](docs/permissions.md) — who can do what: the mixins/`get_object()`
  overrides that gate each view.
- [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) — shipped roadmap items.
- [`ROADMAP.md`](ROADMAP.md) — pending work.

Published at https://reboulip.github.io/famille-busson/ on every push to `main`.
