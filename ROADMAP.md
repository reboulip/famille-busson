# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 2

### Cluster: Documents — visionneuse
- [x] 2.1 · PDF/file viewer overhaul — enlarge the document viewer to use the available
  page space, add a full-screen display mode, add a download button for PDFs, and fix
  the PDF viewer on mobile (currently broken). [#98] [#99] [#100]
- [x] 2.2 · Responsive image viewer & carousel — fit image documents to the viewport
  with zoom support; for documents with multiple images, show a carousel (one image at
  a time on mobile, several on desktop) — final layout to be refined during
  implementation. [#101]

### Cluster: Documents — création & catégorisation
- [x] 2.3 · Require at least one file per document — block saving a `Document` with
  zero `DocumentFile`s. [#97]
- [x] 2.4 · Nested category dropdown — show sub-categories indented under their parent
  in the category `<select>` on the document create/edit form. [#102]
- [x] 2.5 · "Add document" button on category view — pre-fills the category on the
  document creation form. [#96]

### Cluster: Documents — métadonnées & accès
- [x] 2.6 · `Document.redactor` field — optional `Person` FK for the document's
  author/editor, separate from `uploaded_by`. [#107]
- [x] 2.7 · Category view: access & hierarchy — show which groups can access the
  category ("Visible par : ..." / "Tous" if unrestricted) and show parent/child
  categories. [#95]

### Cluster: Markdown
- [x] 2.8 · Fix list rendering after a paragraph — a `- item` list directly following a
  paragraph (no blank line) doesn't render as `<ul>` in the shared `markdown_utils.py`
  pipeline. [#93]
- [x] 2.9 · Consistent markdown rendering on card previews — apply the existing
  `markdown_plain` filter (already used by publications' cards) to document/category
  card excerpts. [#92]
- [x] 2.10 · Markdown editor toolbar — wire the existing Write/Preview widget into the
  documents app's category/document description fields, and add lightweight
  GitHub-style formatting buttons (bold/italic/list/etc.) — scope to be refined during
  implementation. [#94]

### Cluster: Annuaire — profil
- [x] 2.11 · Annuaire sort options — default the directory list to most-recently-created
  first; add sortable birth date and alphabetical name (asc/desc). [#106]
- [x] 2.12 · Edit Profile view buttons — mirror the Save/Edit-relations buttons at the
  top of the page, and add a Cancel button (top + bottom) returning to the profile
  view. [#105]
- [x] 2.13 · Deceased attribute on Person — admin/staff-only `deceased` flag + optional
  death date; when set: suppress birthday notifications, render the photo in greyscale
  with a black border (annuaire, profile, genealogy), and exclude from the "profiles
  without a geolocated address" count. [#104]

### Cluster: Généalogie
- [x] 2.14 · Genealogy export — rename "exporter en excel" to "exporter le carnet
  d'adresse en excel"; add an "exporter en image" button generating a JPEG of the
  displayed tree. (requires: 2.13) [#90]

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

### Cluster: Markdown
- [ ] B.4 · Markdown editor on profile description — wire the same Write/Preview
  widget used elsewhere (see Phase 2's 2.10) into `ProfileEditForm`'s `description`
  field, which today renders as a plain textarea even though it's displayed through
  the markdown pipeline. Surfaced during Phase 2 planning; scoped out of that sprint
  to avoid a `annuaire/forms.py` collision with 2.13. (priority: tbd)

### Cluster: Publications
- [ ] B.5 · Exclude deceased profiles from outbound notifications — new blog-post
  emails (`publications/signals.py`) currently mail every subscriber regardless of
  the `deceased` flag added in Phase 2's 2.13; extend that suppression here too.
  Surfaced during Phase 2 planning; scoped out of that sprint as a separate app's
  concern. (priority: tbd)
