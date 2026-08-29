# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 6

### Cluster: Annuaire — administration
- [x] 6.1 · Bulk account creation: list existing Accounts with no linked Person profile
  yet (invite link unused) to make re-sending links faster. [#86]

### Cluster: Profil
- [x] 6.2 · Suppress the mailto link entirely on the person detail view when the
  profile has no email address (currently renders a link to "None"). [#85]

### Cluster: Généalogie — arbre interactif
- [x] 6.3 · Align the Excel export button with the search field in the genealogy view.
  [#85]
- [x] 6.4 · Allow the interactive genealogy tree to expand full-screen, covering both
  the profile-card panel and the sidebar. [#85]
- [x] 6.8 · Re-fix genealogy tree compact width + spouse-side positioning (reopened —
  the #80/#81 fix shipped in 25786a3 broke name display and was hotfixed back to vendor
  defaults, undoing the compaction and spouse-side change along with it). Compact the
  tree's horizontal width for 3-4 generations and position spouses on the correct side
  (right) of their direct-descendant children, without re-breaking name/label display.
  Must be analyzed and verified with an actual UI check in the dev environment before
  considering it done — do not ship on code-reasoning alone this time. (requires: 6.3,
  6.4 — same files/DOM region) [#81]

### Cluster: Carte
- [x] 6.5 · Collapse the un-geolocated profiles list to one line per profile (account +
  address) instead of two. [#85]
- [x] 6.6 · Center non-square profile pictures within their marker medallion (currently
  left-aligned, leaving a blank strip e.g. for a 1:2 aspect ratio). [#85]
- [ ] 6.7 · Increase carte profile-picture marker size by about 50%. [#85]

## Backlog

> Unscoped items held for a future triage pass — not tied to any phase or sprint.
> Promote an item into a numbered `## Phase N` (with a proper `N.M` id) once it's ready
> to be scoped and sprinted.

### Cluster: Profil — adresse secondaire
- [ ] B.1 · Secondary address on profile — let a member add a secondary address to
  their profile, shown on the Carte view, usable to create/locate their chalet.
  Interacts with the Phase 1 chalets self-service work; scope to be refined.
  (priority: tbd) [#53]

### Cluster: Groupes et permissions
- [ ] B.2 · SCI grand chalet group — new group for grand chalet works/news content,
  with author vs. reader roles (SCI project-group members are authors, SCI
  shareholders are readers). Needs a groups/roles/permissions design pass first — no
  such model exists yet. (priority: tbd) [#57]

### Cluster: Sécurité
- [ ] B.3 · Throttle unauthenticated email-sending endpoints — rate-limit the
  password-reset and magic-link request views; needs a shared cache backend first
  (current `CACHES` setting is unset, defaulting to per-worker `LocMemCache`, which a
  throttle built on it would trivially bypass). (priority: tbd)
