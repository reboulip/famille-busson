# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 7

### Cluster: Publications & Documents

- [x] 7.1 · Make the whole card clickable to its detail — publications
  (`publications/templates/publications/blogpost_list.html`) and documents
  (`documents/templates/documents/document_list.html`, `category_list.html`) lists
  currently link only via the title text. [#128]
- [ ] 7.2 · Documents list row cleanup (`document_list.html`, `category_list.html`):
  replace the subtitle copy, shrink the description font, move category+date to the
  right of the row, tighten row padding/line-height. [#123]

### Cluster: Profil

- [x] 7.3 · Rename the "Coordonnées" section heading to "Informations" on the profile
  view (`annuaire/templates/annuaire/personne_detail.html`). [#122]
- [ ] 7.4 · Mobile profile view (`personne_detail.html`): shrink the sticky identity
  rail on scroll to show only name+photo instead of the full info card, and move
  "Modifier les relations" to the bottom of the page after the relations display
  (optionally same placement on web). [#124]

### Cluster: Généalogie

- [x] 7.5 · Remove the square artifacts rendered under circle nodes in the family
  tree visual (`annuaire/static/js/family_tree.js`). [#121]
- [ ] 7.6 · Mobile genealogy view: shrink the fixed bottom banner as much as possible
  to give the tree visualization more vertical space. [#125]

### Cluster: Chalets et Présences

- [x] 7.7 · Rename the "Chalets" tab/heading to "Chalets et Présences" and reorder
  `chalet_list.html` to show the presence calendar (`_presence_calendar.html`) above
  the chalet list instead of below. [#127]

### Cluster: Carte

- [ ] 7.8 · Map same-address clustering (`annuaire/static/js/map_init.js`): lower the
  zoom threshold at which a cluster explodes into individual markers, and tighten
  marker spacing once exploded so photos sit closer without overlapping. [#126]

### Cluster: Accueil

- [ ] 7.9 · Add an upcoming-birthdays widget to the home page (`annuaire/views.py`'s
  `home()`), listing people with a birthday in the next 8 days, positioned just under
  the date. [#120]

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
