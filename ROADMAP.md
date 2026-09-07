# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 8 — Retours du terrain : e-mails, documents et petites frictions

> Neuf signalements de membres de la famille, accumulés depuis la Phase 7 : deux liens
> cassés dans les e-mails de notification (ils pointent vers `localhost` au lieu du site
> en production), un rappel d'anniversaire resté muet, et une poignée d'améliorations
> ponctuelles côté documents et publications. Rien ici ne dépend du socle que bâtit la
> Phase 9 — ce sont des correctifs et ajustements à absorber avant de s'y engager.

### Cluster: Notifications par e-mail
- [x] 8.1 · Fix notification-email links resolving to `localhost` instead of the
  production domain — affects the "nouvelle publication" link and the "Gérer mes
  préférences" link, the latter also pointing at a stale URL name (`profile/edit`
  instead of `personne/update`). [#132] [#134]
- [x] 8.2 · Enrich publication notification emails — add the author's name after
  "Nouvelle publication", and link the homepage from the banner image and the
  "site de la famille Busson" footer text. [#135] [#136]

### Cluster: Documents et publications
- [x] 8.3 · Document list sorting and filtering — dropdown sort (date de dépôt,
  alphabétique, rédacteur, date de rédaction, croissant/décroissant, le plus récent par
  défaut) plus filtering by author and by year of redaction. [#137]
- [x] 8.4 · Link a publication to a document — from the publication form, attach an
  existing `documents.Document` or create a new one linked to the publication,
  alongside the existing attachment upload. Needs careful UX design for the two entry
  points (link vs. create). [#133]

### Cluster: Interface
- [x] 8.5 · Close button on the publication attachment viewer, to return to the
  publication without relying on the browser back button. [#131]
- [x] 8.6 · Discreet version number in the site footer. [#138]

## Phase 9 — Socle : correctifs, sauvegardes et tâches de fond

> The archive has no backup, the platform has no shared cache, and it cannot do any work
> outside the request/response cycle. This phase fixes the one reopened bug, then builds
> the foundation the next four phases stand on. Deliberately small — but backups come
> before Phase 10 invites the family to pour an irreplaceable photo archive into a box
> nobody has ever restored.

### Cluster: Correctifs
- [x] 9.1 · Fix the mobile sticky profile rail — on mobile the "Informations" panel starts
  scrolling but never collapses, so the Phase 7 fix (`profile_sticky_identity.js`) only
  half works; only name and photo should stay pinned. Reopened by the reporter, whose
  explicit condition is that this is verified visually on a real mobile viewport before
  it ships. [#124]
- [x] 9.11 · Fix birthday reminder emails not being sent — diagnose and repair
  `send_birthday_reminders` so day-before/day-of reminders actually go out; independent
  of the queue migration in 9.6. [#130]

### Cluster: Sauvegardes et restauration
- [x] 9.2 · Automated backups — a repo-tracked script dumping Postgres and archiving
  `media/` and `documents_data/`, with a retention policy and an off-VPS copy, documented
  in `docs/deployment.md` alongside the existing scheduled-task entries.
- [ ] 9.3 · [deferred] Tested restore procedure — a runbook plus an actually-executed restore into a
  scratch container, with the result recorded. A backup nobody has restored is not a
  backup. (requires: 9.2) — **infra shipped** (`scripts/restore.sh`,
  `docker-compose.restore.yml`, `docs/restore.md`); the drill itself is not yet executed
  — see `docs/restore.md`'s empty drill log. Check this off once a drill has actually run
  and been recorded.
- [x] 9.4 · Backup monitoring — alert when a run fails, doesn't happen at all, or produces
  a suspiciously small artifact. (requires: 9.2)

### Cluster: Cache et file de tâches
- [x] 9.5 · Shared cache — add a Valkey/Redis container and set `CACHES`, which is
  currently unset, so every gunicorn worker holds its own `LocMemCache`. Compose, env and
  deployment docs updated together.
- [x] 9.6 · Background task queue — add a job runner and move `send_birthday_reminders`
  and `extract_document_content` off the VPS crontab onto its scheduler. Leaning
  `django-q2` over Celery (one worker container, no separate result backend, fits a
  single VPS); the final choice is a sprint-planning decision. (requires: 9.5)
- [x] 9.7 · Outbound email through the queue, with retries — today a provider hiccup
  during the blog-post notification signal loses the mail silently. (requires: 9.6)
- [x] 9.8 · Throttle unauthenticated email-sending endpoints — rate-limit the
  password-reset and magic-link request views, now that a shared cache exists to build a
  throttle a second worker can't trivially bypass. (requires: 9.5)

### Cluster: Observabilité
- [x] 9.9 · Error monitoring — surface 500s without reading `docker logs`: structured
  logging plus an error tracker (Sentry or a self-hosted equivalent).
- [x] 9.10 · Deepen `/healthz` — check database, cache, queue and storage writability, and
  wire it to the compose healthcheck and an external uptime monitor. (requires: 9.5, 9.6)

## Phase 10 — Photothèque : albums, souvenirs et visages

> Photos are what a family site lives on, and today they exist only as attachments inside
> a publication — no album, no bulk upload, no way to find every photo of one person.
> This phase gives them a home of their own.

### Cluster: Modèle et dépôt
- [x] 10.1 · `Album` and `Photo` models — album (title, markdown description, date range,
  cover, group-restricted visibility mirroring `documents.Category`) and photo (file,
  caption, `taken_at`, uploader, dimensions). Photos are family-private, so they follow
  the protected-storage and access-checked-endpoint pattern of `documents`, never
  `MEDIA_URL`.
- [x] 10.2 · Bulk upload — a multi-file picker with per-file progress and a client-side
  cap, reusing the accept-list template tag and server-side validators already written
  for `documents`. (requires: 10.1)
- [x] 10.3 · Async derivatives — thumbnails, web-size renditions, and EXIF capture date
  and orientation, generated on the queue rather than inside the upload request.
  (requires: 9.6, 10.1)

### Cluster: Parcours
- [x] 10.4 · Album list and album detail — responsive grid, cover images, photo counts,
  and the shared empty state. (requires: 10.1)
- [x] 10.5 · Lightbox viewer — full-screen, keyboard and swipe navigation, one image at a
  time on mobile. Extends the existing document image viewer and carousel rather than
  adding a second implementation. (requires: 10.4)
- [x] 10.6 · Photo detail — caption, date, uploader, the people in it, and an original-file
  download. (requires: 10.1)

### Cluster: Personnes et mémoire
- [x] 10.7 · Tag people in a photo — a through-model linking `Photo` to `Person` via the
  existing person-picker component; a region box is stored but not yet drawn.
  (requires: 10.1)
- [x] 10.8 · Photos tab on the profile — every photo a person is tagged in, on their own
  profile page. (requires: 10.7)
- [x] 10.9 · Link an album to a publication — a blog post references an album instead of
  re-uploading its images. Whether existing `publications.Attachment` images migrate into
  the library is an open decision for sprint planning. (requires: 10.1)
- [x] 10.10 · "Il y a X ans" on the home page — resurface a photo or a publication from
  this date in earlier years, next to the birthdays widget. (requires: 10.3)

## Phase 11 — Recherche et découverte

> Search today is per-app `icontains`: accent-sensitive on SQLite ("Bus" never matches
> "Büsson"), unranked, and unable to look across people, publications, documents and
> photos at once.

### Cluster: Recherche globale
- [x] 11.1 · Search backend — a shared abstraction over Postgres full-text search
  (`SearchVector`/`SearchQuery`, unaccented and ranked) with a SQLite fallback, because
  production is Postgres while development and the entire test suite run on SQLite.
- [x] 11.2 · Search indexes — a `SearchVectorField` and GIN index on `Person`, `BlogPost`,
  `Document` (folding in the existing `extracted_text`), `Album` and `Photo`, refreshed on
  the queue when a row changes. (requires: 9.6, 10.1, 11.1)
- [x] 11.3 · Global search UI — a search field in the topbar and a results page grouped by
  type, enforcing every existing access rule: a locked `documents.Category`'s content must
  never surface in results. (requires: 11.2)

### Cluster: Navigation et étiquettes
- [x] 11.4 · Tags on publications — a tag many-to-many with chips on cards and filtering,
  which also gives the family-specific `BlogPost.post_type` ("Busson connection") a
  generic successor for Phase 16 to migrate onto.
- [x] 11.5 · Activity feed — one "Quoi de neuf" view merging new publications, comments,
  documents, photos and members since the viewer's last visit.
- [x] 11.6 · Onboarding empty states — extend the shared `_empty.html` with "commencez
  par…" guidance, so a brand-new member's first visit isn't a series of empty pages.

## Phase 12 — Événements et calendrier partagé

> Présences cover who is at a chalet and when. Nothing covers the rest of the family's
> shared time — a réunion de famille, a baptême, a repas — and nothing puts all of it in
> one place, or into the calendar app people actually use.

### Cluster: Événements
- [x] 12.1 · `Event` model and CRUD — title, markdown description, start and end, all-day
  flag, location (reusing the address picker and geocoding), organisers, and
  group-restricted visibility.
- [ ] 12.2 · RSVP — a per-`Person` participation record (oui / non / peut-être, guest
  count, note) with the attendee list shown on the event page. (requires: 12.1)
- [ ] 12.3 · Event notifications — an announcement on creation and a reminder before the
  date, honouring the existing `Settings` notification preferences and the deceased-profile
  suppression already applied to the other outbound mail. (requires: 9.6, 12.1)

### Cluster: Calendrier unifié
- [ ] 12.4 · One calendar — events, chalet présences and anniversaires in a single
  month/agenda view with per-type filters, generalizing `presence_calendar.js` rather than
  standing up a second calendar implementation. (requires: 12.1)
- [ ] 12.5 · iCal subscription — a per-account tokenised `.ics` feed, so the family
  calendar appears in Google or Apple Calendar and stays in sync. (requires: 12.4)
- [ ] 12.6 · Events on the home page and the map — an upcoming-events card, and event
  markers alongside the existing person and chalet markers. (requires: 12.1)

## Phase 13 — Généalogie approfondie

> The tree draws relationships well but holds almost no genealogical data — no places, no
> marriage dates, no stories, no sources — and it can't exchange any of it with the tools
> family members already use.

### Cluster: Données généalogiques
- [ ] 13.1 · Vital data — birth and death place on `Person`; marriage place, date and end
  date on `Relation`, surfaced on the profile and in the tree. Follows the established
  precedent for sensitive personal fields: a concrete technical necessity, and the
  smallest display surface that serves it.
- [ ] 13.2 · Life stories — a dated markdown story attached to a `Person`, optionally
  illustrated from the photo library, rendered as a timeline on the profile.
  (requires: 10.1)
- [ ] 13.3 · Sources — a lightweight citation record that a story or a vital-data claim can
  point at, so provenance survives the person who knew it. (requires: 13.2)

### Cluster: Interopérabilité
- [ ] 13.4 · GEDCOM export — export the tree, or a selected subtree, so members can load it
  into Geneanet, MyHeritage or Gramps. (requires: 13.1)
- [ ] 13.5 · Person merge — detect likely-duplicate `Person` rows and merge them safely
  across relations, photos, documents, présences and account link. A prerequisite for
  import, which would otherwise multiply the directory.
- [ ] 13.6 · GEDCOM import — parse into staged records behind a review-and-merge screen; no
  row is written to the directory until a human approves it. (requires: 13.4, 13.5)

### Cluster: Confidentialité
- [ ] 13.7 · Living-person privacy — exports, and any future surface beyond logged-in
  members, redact living people's details by default, with an explicit per-person setting.
  (requires: 13.4)

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
