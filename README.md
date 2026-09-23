# famille-busson

A private website for a family. It includes:

- a member directory (`annuaire`) with family relations and an interactive family tree;
- a list of family houses ("résidences"), with a calendar of who stays there and when;
- a map of members and houses;
- a site-wide search and an activity feed ("Quoi de neuf");
- a small blog (`publications`) with tags, comments and attachments;
- a document library (`documents`) and a photo library (`photos`), both restricted by
  group;
- life stories with sources (`genealogy`) on each profile.

Each installation can have its own name, colours and logo (see
[`docs/installation.md`](docs/installation.md)). The app uses Django 6 and Python 3.13.
It runs on a single server and is deployed automatically.

## Quickstart

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py populate_dev_data   # creates test data and test logins
uv run python manage.py runserver
```

The full list of dev commands, with the test logins, is in
`.claude/skills/dev-commands/SKILL.md`.

## Documentation

- [`docs/installation.md`](docs/installation.md) — start here to set up a new
  installation.
- [`docs/data_model.md`](docs/data_model.md) — the data model. Generated from the code.
- [`docs/deployment.md`](docs/deployment.md) — how the app is deployed to production.
- [`docs/design_system.md`](docs/design_system.md) — the visual style, and the rules to
  follow when you add a page.
- [`docs/emails.md`](docs/emails.md) — the emails the site sends, and how to preview
  them.
- [`docs/permissions.md`](docs/permissions.md) — who can do what.
- [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) — work already shipped.
- [`ROADMAP.md`](ROADMAP.md) — work still to do.

The documentation is published at https://reboulip.github.io/famille-busson/ on every
push to `main`.
