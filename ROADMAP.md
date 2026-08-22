# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 1

### Cluster: Chalets en libre-service
- [x] 1.1 · Open chalet creation to all accounts — chalet creation is currently
  staff-only; allow any authenticated account to create a chalet, auto-assign the
  creator as an owner, and let additional owners be added at creation time using the
  existing person-picker JS component. (priority: medium) [#48] [#52]
- [x] 1.2a · Chalet address picker and GPS coordinates — reuse the person address BAN
  API picker for the chalet address field, capture and store GPS coordinates the same
  way. `Chalet.gps_coordinates` (free-text) is kept as-is for now, just unused by the
  new picker. (priority: medium) [#54] (split from 1.2)
- [x] 1.2b · Add chalets to the Carte view — extend the carte's avatar-marker approach
  (item 1.4) to chalet markers. (priority: medium) [#54] (split from 1.2, requires:
  1.2a, 1.4)
- [x] 1.3 · Populate the home page Chalets card — currently empty even when chalets
  and presences exist; populate it the same way as the other home page cards.
  (priority: medium) [#55]

### Cluster: Carte
- [x] 1.4 · Fix missing profile pictures on the carte view — markers display
  correctly but profile pictures don't render. (priority: medium) [#49]

### Cluster: Profil et authentification
- [x] 1.5 · Line breaks between contact info types — annuaire profile display should
  systematically break to a new line between each type of contact info (email,
  phone, etc.), including on mobile. (priority: low) [#47]
- [x] 1.6 · Show/hide password toggle at login — let a user reveal the password they
  just typed on the login form for verification, via a standard show/hide toggle.
  (priority: low) [#50]

### Cluster: Navigation
- [x] 1.7 · Link to GitHub issues from the site — add a link so members can report
  bugs directly. (priority: low) [#51]
- [x] 1.8 · Home page link in the navigation bar — currently no way to get back to
  the home page from elsewhere in the site; add a nav link. (priority: low) [#56]

### Cluster: Généalogie — arbre interactif
- [x] 1.9a · Fix genealogy view rendering/UX bugs — search results render
  black-on-black; empty parent nodes show a confusing "ADD" placeholder (now left
  empty); edges between nodes are missing; selecting a node to show the detail panel
  de-centers the tree; and node labels don't show the full name. (priority: high)
  [#59] (split from 1.9)
- [x] 1.9b · Drop `Person.gender` — investigation confirmed the feature works without
  it (family-chart only used it cosmetically); approved by the user, drop the field,
  migration, form field, and family-chart payload key, with a generation-depth CSS
  accent replacing the lost card color cue. (priority: high) [#59] (split from 1.9,
  requires: 1.9a)

## Phase 2

### Cluster: Profil et authentification
- [x] 2.4 · Extend the password show/hide toggle to other password forms — wire the
  existing `password_toggle.js` into `signup.html`, `password_reset_confirm.html`, and
  `password_change_forced.html` via `{% block extra_js %}`; also fixed a latent bug where
  the toggle's DOM wrapping broke Bootstrap's field-error visibility on these
  field-error-raising forms. (priority: low) [#64]

### Cluster: Généalogie — arbre interactif
- [x] 2.5 · Default to the genealogy tree's biggest branch — the bare `/genealogie/`
  route now always centers on the biggest branch's anchor, replacing the previous
  own-profile default. (priority: low) [#67]
- [x] 2.6 · Sort genealogy tree children by age — siblings are ordered oldest-first
  within each couple's children, unknown birth dates last. (priority: low) [#61]

### Cluster: Navigation
- [x] 2.7 · Reword the GitHub issue link — label changed to "Signaler un bug ou
  proposer une évolution" to also invite feature suggestions, not just bug reports.
  (priority: low) [#66]

### Cluster: Généalogie — enfants sans compte
- [ ] 2.8a · Accountless profile creation with ownership — let any registered account
  create a new `Person` profile with no linked `Account`, behind a clear warning that
  this path is only for people who should not get site access (children, other family
  members). The creating account becomes the profile's initial owner; an "owners"
  relation — restricted to profiles with no linked `Account` — lets current owners add
  or remove other owners. Owners can edit the profile like their own, but cannot delete
  it — deletion stays admin-only (Django admin). Scope to be refined. (priority: tbd)
  [#60] (split from 2.8)
- [ ] 2.8b · First-login redirect when a profile already exists — when an `Account` is
  later created for someone who already has an accountless `Person` profile (auto-linked
  by the existing post-save signal), the forced first-connection password-reset flow
  must redirect to edit that existing profile, not to the 2.8a creation view. (priority:
  tbd) [#60] (split from 2.8, requires: 2.8a)
- [ ] 2.8c · Claim an existing accountless profile during onboarding — when an
  authenticated account has no linked `Person` (a staff-created account, or a fiche with
  a missing/stale email), offer a self-service search over accountless profiles from the
  profile-creation page; selecting one links the account instantly, no approval step. The
  signup email gate (an email must already match a `Person` to self-register) is
  unchanged — this is deliberately not exposed on the public signup form. Surfaced during
  Phase 2 sprint planning (no GH issue). (priority: tbd) (requires: 2.8a, 2.8b)

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
