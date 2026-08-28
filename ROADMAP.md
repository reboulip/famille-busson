# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 5

### Cluster: Carte
- [x] 5.1 · Un-geolocated profiles list — on the Carte view, list profiles lacking a
  geolocated address with links to their profile; also show an "adresse non
  géolocalisée" notice on the profile form when geocoding fails. [#83]
- [x] 5.3 · Spread clustered map markers — when multiple profiles share the same
  address, offset their markers around the perimeter of a circle centered on the
  shared point (varying distance/angle) so overlapping profile pictures stay visible.

### Cluster: Généalogie — arbre interactif
- [x] 5.2 · Genealogy tree rendering fixes — compact the tree's horizontal width for
  3-4 generations, position spouses on the correct side of direct descendants, and
  stop long names from being clipped. [#80] [#81]

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
