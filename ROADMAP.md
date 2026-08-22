# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 3

### Cluster: Carte
- [x] 3.1 · Person search in Carte — select a person, center the map on their
  address. (requires: 3.2) [#75]
- [x] 3.2 · Multiple members at the same address — show all members sharing an
  address instead of just one (split marker / cluster with names+photos on click).
  [#68]

### Cluster: Adresses
- [ ] 3.3 · Worldwide address support — extend the BAN-only address autocomplete
  (`address_picker.js`, `annuaire/forms.py`) so non-French addresses can be entered
  and geocoded. [#73]
- [x] 3.4 · Drop Chalet.gps_coordinates free-text field — verify production
  contents, then remove the field, its form usage, and its display on
  `chalet_detail.html`, with a migration. [#63]

### Cluster: Profil
- [x] 3.5 · Editable notification/subscription preferences — expose the
  profile-creation-time notification checkboxes in the profile edit form so they
  can be changed afterward. [#71]

### Cluster: Authentification
- [ ] 3.6 · Magic Link login — passwordless email login reusing the existing
  one-time-link primitive (`_build_password_reset_url()`, `annuaire/views.py`) and
  configured email delivery, pointed at `login()` instead of the password-reset
  flow. Must preserve the closed-signup guard (`Account` only links an existing
  `Person` by email, never auto-provisioned from the link). OIDC and Passkeys
  remain out of scope. [#74]

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
