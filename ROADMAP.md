# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 4

### Cluster: Documents

- [ ] 4.1 · Fix PDF viewer (`documents/static/js/document_viewer.js`'s `renderPdf()`):
  first pages are hidden, and the viewer opens scrolled to the last/a far page instead
  of page 1 — likely the same root cause. [#109]
- [ ] 4.2 · Fix document image viewer (`documents/static/js/document_viewer.js`,
  `.document-viewer-zoomable`): click-to-zoom isn't working; multi-image documents
  should step through one image at a time in fullscreen instead of showing them all at
  once. [#111]
- [ ] 4.3 · Add a "+ Ajouter un document" button to `document_list.html`
  (`DocumentListView`), matching the one already on `category_detail.html`. [#115]
- [ ] 4.4 · Allow selecting multiple files at once for a document's attachments
  (`documents/forms.py`'s `BaseDocumentFileFormSet`, `document_form.html`) instead of
  attaching one file per file-picker round-trip. [#116]

### Cluster: Annuaire

- [ ] 4.5 · Make the directory list (`DirectoryListView`, `annuaire_list.html`) filter
  live: apply `sort` immediately on change and debounce `q` (~200ms) instead of
  requiring the "Rechercher" button; remove the button once both are automatic. [#110]

### Cluster: Généalogie

- [ ] 4.6 · Fix genealogy tree image export (`family_tree.js`'s `htmlToImage.toJpeg`
  call): raise output resolution so large/main-branch exports stay legible, and fix
  relationship connector lines missing from the captured image. [#113]

### Cluster: Carte

- [ ] 4.7 · Same-address people on the map (`annuaire/static/js/map_init.js`) spread
  into individual markers up to `SPREAD_MAX` (8); extend the existing "+N"
  cluster-badge marker (already used above that threshold) to same-address groups of
  any size instead of spreading small ones. [#114]

## Phase 5

### Cluster: Emails — identité visuelle

- [ ] 5.1 · Shared email design system — spec pass — detailed visual specs + static
  mockups for one common branded HTML email base (header/logo/colors/footer,
  unsubscribe-link placement), covering all 5 existing app email touchpoints: the
  birthday-reminder and new-blog-post notifications (`annuaire/email_utils.py`'s
  `send_bulk_emails`, currently inline plain-text f-strings in
  `publications/signals.py` / `send_birthday_reminders.py`), the bulk-account-
  creation/resend email (`annuaire/views.py`'s `_account_setup_email_content`, same),
  and the two `PasswordResetView`-based flows (password reset, magic link — already
  template-file-based but text-only). No existing brand system beyond the
  mountain/trees favicon (`annuaire/static/favicon.svg`) — starts mostly from scratch.
  Must be email-safe HTML (inline CSS, table-based layout for Outlook) with a
  plain-text fallback for every message, not modern CSS. Store specs/mockups in a
  throwaway folder outside `docs/` and outside any app's `templates/` dir (e.g.
  `design/emails/`) — not wired into Django's template loader, for review before 5.2
  builds anything.
- [ ] 5.2 · Shared email design system — build — implement the reviewed spec as real
  template(s) and wire all 5 flows onto it. Trigger/filter/subscriber logic for the
  birthday and new-post notifications is unchanged — opt-in checkboxes, deceased-
  profile exclusion, and the connection-cycling bulk sender all already shipped
  correctly (#39, Phase 3 wave 2) — this is a content/rendering swap only. The 3
  raw-`send_mail` flows need to move to multipart sending (`EmailMultiAlternatives` or
  `send_mail(html_message=...)`); the 2 `PasswordResetView`-based flows just need
  `html_email_template_name` set to the new template. (requires: 5.1)

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
