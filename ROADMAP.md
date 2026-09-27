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

## Phase 18 — Corrections diverses et confort d'usage

> A batch of field-reported fixes and small comfort improvements, triaged from GH issues.

### Cluster: Authentification
- [ ] 18.1 · Self-service login link resend — a user with an expired login link lands on
  a page to request a new one (valid 24h) instead of needing an admin reset. [#147]

### Cluster: Annuaire
- [ ] 18.2 · Rename relation labels — "Mariage" becomes "Mariage ou Pacs" and "Conjoint"
  becomes "En couple" everywhere the labels appear (forms, family tree, GEDCOM export,
  audit log). [#148]

### Cluster: Infrastructure et CI
- [ ] 18.3 · Fix weekly dependency-upgrade workflow — resolve the ruff check failure
  blocking `dependency-upgrade.yml`, and make the check auto-format where possible. [#149]

### Cluster: Carte
- [ ] 18.4 · Bring map tiles into OSM policy compliance — proper Referer/User-Agent
  identification and HTTP caching so tile requests aren't blocked by OpenStreetMap's
  usage policy. [#150]

### Cluster: Interface et navigation
- [ ] 18.5 · Restore GitHub issue-reporting link in the menu — bring back the link to
  file a bug or suggestion that used to be at the bottom of the menu. [#153]
- [ ] 18.6 · Reposition the site version number — move it from floating mid-page into
  the fixed left sidebar, next to the logout button. [#155]

### Cluster: Calendrier
- [ ] 18.7 · Add a real calendar grid to the Calendrier tab — a month view showing
  events, presences and birthdays, not just navigation controls and personal-calendar
  export links. [#154]

## Phase 19 — Bulletins familiaux : import et rendu

> Dozens of scanned family bulletins (*Busson's Connection*, 1990s) are to become web
> pages that always render the same way. An AI agent turns each PDF into a validated
> JSON + pictures package. That step is prototyped on BC n°17, and the spec, schema and
> working prototype are in `design/bulletins/`. This phase brings those packages into
> `publications`.

### Cluster: Bulletins familiaux
- [ ] 19.1 · Bulletin import and rendering. Staff upload a bulletin package (a zip of
  `bulletin.json` + `images/`). It is validated against
  `design/bulletins/bulletin.schema.json` plus integrity checks and previewed, then
  stored as a new `Bulletin` model: the JSON is the source of truth, the pictures are
  files. It renders with fixed templates as list and detail pages that use the full
  screen width: **pictures dock right with the text wrapping around them**, several
  pictures with little or no text form a **carousel**, and **every picture has a
  caption** (captions added during transcription are marked). Tables stack on phones,
  and there is a dark mode and a self-hosted Caveat font. Spec: `design/bulletins/SPEC.md`:
  §2 package (schema 0.2) and transcription conventions, §3 rendering (§3.1 docking,
  carousels, captions), §4 import requirements. The prototype templates, CSS and JS in
  `design/bulletins/prototype/` are meant to be lifted as-is, and
  `prototype/fixtures/demo-001/` is a ready synthetic test fixture. Settle the open
  questions in §6 first: model choice, storing the original PDF, visibility of
  addresses and phone numbers.

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
