# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 1

> Document management: a new `documents` app (upload/browse/view/edit family
> documents, PDF/doc/image support, group-restricted categories) plus the shared
> Markdown rendering it needs for `Category.description`, extended to `publications`
> for consistency.

### Cluster: Rendu Markdown
- [x] 1.1 · Shared Markdown rendering — sanitized Markdown (Python-Markdown + `nh3`,
  `nl2br` extension so existing single-newline content renders unchanged) as a shared
  template filter, with a server-side preview endpoint reused by every Markdown field.
- [x] 1.2 · Write/Preview widget — reusable Write/Preview tabs wired to 1.1's preview
  endpoint, applied to `BlogPost.body` and `Comment.body`. (requires: 1.1)

### Cluster: Gestion des groupes
- [x] 2.1 · Group management UI — staff-only screens to create/rename/delete
  `auth.Group` and manage membership, reusing the existing `Account.groups` M2M. Lays
  groundwork also needed by Backlog B.2.
- [x] 2.2 · Group-deletion guard — refuse to delete a `Group` while any `Category`
  still restricts access to it. (requires: 3.1)

### Cluster: Modèle documentaire & stockage protégé
- [x] 3.1 · `Category` & `Document`/`DocumentFile` models — nested `Category`
  (self-FK, Markdown description via 1.1) restricted to an `auth.Group` set only where
  the whole ancestry is public (a restricted parent's descendants inherit its groups
  and freeze); `Document` (title, nullable `document_date`, description) +
  `DocumentFile` (file, caption); category deletion `PROTECT`ed while non-empty.
  (requires: 1.1)
- [x] 3.2 · Protected file storage — storage location outside `MEDIA_ROOT`/
  `media_serve`'s reach (new `/srv/bubu/data/documents` volume alongside the existing
  media/postgres ones), extension allowlist + 50 MB size cap enforced server-side,
  `file_cleanup` signal wiring for `DocumentFile.file` and generated thumbnails.
  (requires: 3.1)

### Cluster: Parcours documents
- [x] 4.1 · Document CRUD — create/update/delete views (title/date/category/files),
  uploader-or-staff ownership (mirrors `AuthorOrStaffRequiredMixin`), detail view
  branching preview by type (image inline, PDF embed, else download).
  (requires: 3.2)
- [x] 4.2 · Category-aware browsing — document list (search, category filter,
  pagination) and category list/detail views, filtered by the viewer's effective
  group access; staff-only category create/update/delete views. (requires: 2.1, 3.1)
- [x] 4.3 · Protected download/preview endpoint — dedicated per-file URL that
  re-checks the category's effective group access before streaming, independent of
  `media_serve`. (requires: 3.2, 4.2)
- [x] 4.4 · Nav + docs — "Documents" sidebar entry, `docs/data_model.md`
  regeneration, `docs/deployment.md` updates for the new volume/cron entries.
  (requires: 4.1, 4.2, 4.3)

### Cluster: Recherche & traitement différé
- [ ] 5.1 · Content extraction pipeline — `manage.py` command backfilling PDF text
  (PyMuPDF) with Tesseract OCR fallback for image-only pages/scans, plus a
  first-page thumbnail; run on a cron schedule like the existing reminder commands.
  (requires: 3.2)
- [ ] 5.2 · Content search — extend document search to the extracted-text column.
  (requires: 5.1, 4.2)
- [x] 5.3 · CI system dependency — install `tesseract-ocr` (+ `fra` language pack)
  in the `Dockerfile` and the `tests.yml` runner so OCR-path tests exercise the real
  binary. (requires: 5.1)

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
