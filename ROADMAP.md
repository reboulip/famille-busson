# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 9 — Socle : correctifs, sauvegardes et tâches de fond

> The archive has no backup, the platform has no shared cache, and it cannot do any work
> outside the request/response cycle. This phase fixes the one reopened bug, then builds
> the foundation the next four phases stand on. Deliberately small — but backups come
> before Phase 10 invites the family to pour an irreplaceable photo archive into a box
> nobody has ever restored.

### Cluster: Sauvegardes et restauration
- [ ] 9.3 · [deferred] Tested restore procedure — a runbook plus an actually-executed restore into a
  scratch container, with the result recorded. A backup nobody has restored is not a
  backup. (requires: 9.2) — **infra shipped** (`scripts/restore.sh`,
  `docker-compose.restore.yml`, `docs/restore.md`); the drill itself is not yet executed
  — see `docs/restore.md`'s empty drill log. Check this off once a drill has actually run
  and been recorded.

## Phase 14 — Vie privée et traçabilité

> The site holds a lot of personal data about identifiable EU residents, and currently
> offers no way to export it, no way to erase it, and no record of who changed what.

### Cluster: Données personnelles
- [ ] 14.1 · Personal data export — a member downloads everything the site holds on them
  (profile, publications, comments, documents, photos, présences) as a single archive.
- [ ] 14.2 · Erasure and anonymisation — a staff flow anonymising a person while preserving
  referential integrity (their publications survive under an anonymised author), with a
  written policy on what is retained and why. (requires: 14.1)
- [ ] 14.3 · Privacy notice — a French page describing what is collected and why, linked
  from signup and the sidebar, with acceptance recorded.

### Cluster: Traçabilité
- [ ] 14.4 · Audit log — who changed or deleted what, and when, across `Person`,
  `Relation`, `Document`, photos and group membership. Staff-visible. Matters here because
  members can already edit each other's profiles through `Person.owners`.
- [ ] 14.5 · Corbeille — deletions on the destructive paths (publications, documents,
  photos, personnes) become recoverable for a retention window instead of immediate.
  (requires: 14.4)

## Phase 15 — Le site devient configurable

> The first of two phases toward a site another family can run. This one removes the
> Busson identity and the French-only assumption from the code, without yet touching the
> domain model or the package name.

### Cluster: Identité configurable
- [ ] 15.1 · `SiteConfig` — a singleton holding site name, wordmark, tagline, sender
  address, feedback URL, timezone and default language; editable by staff and exposed to
  every template through a context processor.
- [ ] 15.2 · Strings out of the templates — every "Famille Busson" and "les Busson" in the
  templates and in all five email templates reads from `SiteConfig` instead.
  (requires: 15.1)
- [ ] 15.3 · Configurable brand — the Alpenglow/Nightfall token layer becomes one named
  theme with a small overridable set of brand colours, plus logo and favicon upload. Both
  palettes must still clear their documented contrast ratios after an override, so the
  accessibility sweep is part of the item, not a follow-up. (requires: 15.1)

### Cluster: Internationalisation
- [ ] 15.4 · i18n scaffolding — `LocaleMiddleware`, `gettext` over every user-facing string
  in templates, forms, model `verbose_name`s and emails, and `makemessages`/
  `compilemessages` wired into CI. French stops being hardcoded and becomes an extracted
  locale. This is the single largest item in the roadmap — hundreds of strings across
  every template — and the wave carrying it should carry little else.
- [ ] 15.5 · English locale and language switcher — a second locale proving the scaffolding
  actually works, plus a per-account language preference. (requires: 15.4)

## Phase 16 — Réutilisable par une autre famille

> The second half: generalize the domain vocabulary, rename the package, and make a fresh
> instance something a person can stand up from a written recipe rather than by reading
> the source.

### Cluster: Modèle de domaine générique
- [ ] 16.1 · `Chalet`/`PresencePSV` become generic — a `Place`/`Stay` pair with a
  configurable label ("Chalet", "Maison", "Résidence"), which is where the "PSV" family
  jargon finally disappears. Model rename plus migration, templates, JS and tests.
  (requires: 15.1)
- [ ] 16.2 · Publication taxonomy — the hardcoded `BlogPost.post_type` "Busson connection"
  choice is replaced by the configurable tags from Phase 11, with a data migration.
  (requires: 11.4)
- [ ] 16.3 · Vocabulary review — relation labels, default group names, seeded document
  categories, and the remaining France-specific defaults (the BAN-first geocoder order,
  the `fr` language default) reviewed for a family that isn't this one. (requires: 15.4)
- [ ] 16.4 · Rename the project package — `famille_busson` becomes a neutral name across
  settings, WSGI/ASGI, `manage.py`, `pyproject.toml`'s pytest config, the Dockerfile's
  gunicorn `CMD`, the compose files and the docs.

### Cluster: Démarrage et vérification
- [ ] 16.5 · `manage.py bootstrap_site` — an interactive first run: site identity, first
  superuser, default groups, starter document categories. (requires: 15.1)
- [ ] 16.6 · Deployment recipe — a templated compose file and `.env`, plus a "start here"
  guide covering DNS, TLS, an email provider, the backup job and the scheduler.
  (requires: 9.2, 9.6)
- [ ] 16.7 · Reusability test — stand up a second, differently-branded instance from a
  clean checkout, following only the recipe, and fix everything it surfaces. The phase
  isn't done until this passes. (requires: 16.4, 16.5, 16.6)

## Backlog

> Unscoped items held for a future triage pass — not tied to any phase or sprint.
> Promote an item into a numbered `## Phase N` (with a proper `N.M` id) once it's ready
> to be scoped and sprinted.

### Cluster: Engagement
- [ ] B.1 · Digest email — a weekly or monthly summary of what happened on the site, so
  members who don't log in still hear from it. (requires: 9.6)
- [ ] B.2 · In-app notification centre — replaces "email or nothing" with a read/unread
  inbox: comments on your publications, tags in photos, event invitations.
- [ ] B.3 · Comment replies and @mentions — threaded replies, and mentioning a member by
  name, each notifying the person concerned.
- [ ] B.4 · Reactions — a lightweight acknowledgement on publications, comments and photos,
  for the many readers who never comment.
- [ ] B.5 · PWA — installable on a phone home screen, with web push carrying the
  notifications above. (requires: B.2)

### Cluster: Chalets et présences
- [ ] B.6 · Booking conflicts and capacity — nothing today prevents two overlapping
  `PresencePSV` rows on the same chalet, or more people than there are beds.
- [ ] B.7 · Frais et travaux — shared expense tracking and a works log per chalet.

### Cluster: Administration des membres
- [ ] B.8 · Self-serve invitations — a member invites a relative, with the invitation's
  state visible and re-sendable; extends today's staff-only bulk account creation.
- [ ] B.9 · Incomplete-profile nudges — surface a missing photo, address or birth date to
  the member concerned, rather than to nobody.

### Cluster: Infrastructure
- [ ] B.10 · Object storage — move media and document storage to an S3-compatible provider.
  Changes the protected-document serving path, which is currently a deliberate local-disk
  design (`DocumentStorage.url()` raises on purpose).
- [ ] B.11 · Multi-tenancy assessment — one deploy serving several families, each on its
  own subdomain. Explicitly *not* the chosen path: Phases 15–16 make the app a
  single-tenant template instead. Kept here as the costed alternative — a tenant model
  scoping every query, per-tenant media isolation, a person belonging to several families,
  a cross-tenant leak test suite, and a data-processor posture including a DPA. Roughly
  four to five phases, touching every view and every test.
