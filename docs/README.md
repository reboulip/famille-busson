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
- [`restore.md`](restore.md) — the backup restore runbook: prerequisites, the drill vs.
  a real restore, verification checklist, and the drill log.
- [`background_tasks.md`](background_tasks.md) — the django-q2 job queue: architecture,
  current scheduled jobs, local dev, and monitoring.
- [`observability.md`](observability.md) — structured logging, request correlation,
  and Sentry error monitoring.
- [`design_system.md`](design_system.md) — the Alpenglow/Nightfall design system:
  where the CSS lives, the colour and typography rules, and the checklist for adding
  a new view. Implements the design pass in `design/web/SPEC.md`.
- [`emails.md`](emails.md) — the five outgoing emails: how each is built, the rules
  email-safe HTML imposes, the embedded birthday photo, and `manage.py preview_emails`.
- [`permissions.md`](permissions.md) — who can do what: the mixins/`get_object()`
  overrides that gate each view, by view.
- [`authentication.md`](authentication.md) — how the magic-link (passwordless) login
  flow works, in French. Complements `permissions.md`'s security-surface notes with
  the full step-by-step flow and design rationale.
- [`search.md`](search.md) — the global search field: the two sidebar/topbar mounts,
  the 2-character minimum, the grouped-preview/"Voir tout" results page, and how to
  manually verify Postgres ranking (no Postgres CI leg this sprint).
- [`privacy.md`](privacy.md) — Phase 14's privacy features: personal data export
  (categories, scope, and access model), the erasure/anonymisation policy, and the
  privacy notice/consent record.
- [`audit.md`](audit.md) — the staff-only audit log: what's tracked and excluded, how
  the acting account is captured per-request, and the row-survival design.
- [`corbeille.md`](corbeille.md) — the soft-delete/restore/purge trash for publications,
  documents, albums and photos: scope, the `soft_delete()`/never-override-`delete()`
  design, the no-cascade rule, and the daily automatic purge job.
- [`site_config.md`](site_config.md) — Phase 15's `SiteConfig` singleton: the
  fields it holds, how `get_site_config()` caches and never auto-creates a row,
  the per-request timezone activation, the staff-only edit screen, the
  conditional first-run seeding migration, (15.2) how templates and emails
  now read `site_name`/`wordmark`/`sender_address`/`feedback_url` from it
  instead of hardcoding "Famille Busson", and (15.3) the configurable
  theme/brand-colour/logo/favicon fields, their WCAG contrast validation, and
  the public `/branding/<kind>` asset route.
- [`i18n.md`](i18n.md) — Phase 15's internationalization: (15.4) the
  `LANGUAGES`/`LOCALE_PATHS`/`LocaleMiddleware` setup, how model/view/template/JS
  strings are wrapped for translation, the `/jsi18n/` catalog route, and the
  makemessages/msgen/compilemessages workflow; (15.5) the fully-translated English
  locale, the `Account.language`/`SiteConfig.default_language`/cookie/browser
  resolution precedence, the `/annuaire/langue/` switcher, and how to add a further
  language.
- [`ROADMAP_ARCHIVE.md`](ROADMAP_ARCHIVE.md) — history of roadmap items already shipped
  to production. Items are moved here from `ROADMAP.md` at release time (see the
  `/release` skill) so `ROADMAP.md` only ever shows pending work.
