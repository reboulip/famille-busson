# Roadmap Archive

Roadmap items that have shipped to production. Moved here from `ROADMAP.md` at release
time (see the `release-workflow` skill), so `ROADMAP.md` only ever shows pending work.

## v0.5.0

### Généalogie — arbre interactif
- **Interactive family tree view** — new `/annuaire/genealogie/` page building a
  genealogy graph from `Relation` records, rendered with the `family-chart` JS library
  (vendored, along with its `d3` dependency, under `annuaire/static/vendor/`). Supports
  incremental exploration from any profile (`/annuaire/genealogie/<pk>/`, also linked
  from each profile page) and a branch picker covering every disconnected family
  component, since the library renders one ego-centric tree at a time rather than a
  single unified overview. Clicking a card opens an inline detail panel (photo, birth
  year, parent/spouse/child chips, link to the full profile) without moving the tree; a
  built-in search finds anyone by name. Added `Person.gender` (nullable, not displayed
  on the profile page — collected only because the rendering library requires it) and
  reworked `populate_dev_data`'s relation seeding to build one coherent multi-generation
  family instead of fully random pairs. [#40]

## v0.4.0

### Annuaire — administration
- **Resilient bulk account creation** — `BulkAccountCreateView` was failing partway
  through batches of ~30+ accounts, most likely because it opened a fresh SMTP
  connection per email, pushing the request past the provider's per-request timeout.
  Now reuses a single connection across the batch, cycling it periodically (and after
  any failed send), and isolates per-account creation failures so one bad row no longer
  500s the rest of the batch. [#41]

### Annuaire — profile improvements
- **Removed postal address from directory list cards** — `annuaire_list.html` cards now
  show only the profile picture and name; the address stays visible on the profile
  detail page. [#43]

### Annuaire — carte
- **Interactive map view of member locations** — new "Carte" view (`/annuaire/carte/`)
  plotting each member's geocoded address as a marker, using Leaflet + OpenStreetMap
  tiles, vendored under `annuaire/static/vendor/leaflet/` (no API key, no CDN). The BAN
  address picker now also captures and stores the coordinates the API always returned
  but previously discarded (`Person.latitude`/`longitude`); a one-time
  `geocode_person_addresses` management command backfills coordinates for members who
  already had an address on file. Profiles with no address, or one that couldn't be
  geocoded, are excluded from the map instead of breaking the view. [#44]

### Notifications — abonnements
- **Per-profile notification subscriptions** — new `Settings` model (one-to-one with
  `Person`) with opt-in checkboxes for birthday reminders and new-blog-post
  notifications, exposed on the profile creation form. New-post notifications fire via a
  `BlogPost` post_save signal; birthday reminders are sent by a new
  `send_birthday_reminders` management command meant to run daily via cron/systemd (no
  in-app scheduler exists in this project). Both reuse a shared, connection-cycling
  resilient-send helper (`annuaire/email_utils.py`) extracted from the bulk-account-
  creation fix above. [#39]

## v0.3.0

### Security
- **Replace plaintext password in the account creation/reset email** —
  `BulkAccountCreateView._send_account_credentials_email` sent the temporary password in
  plaintext by email. Replaced with a single-use, time-limited password reset link
  (`django.contrib.auth.tokens.PasswordResetTokenGenerator`-based), modeled on Django's
  standard `django.contrib.auth` flow.
- **Require authentication for the home page** — the `home` view (`annuaire/views.py`)
  had no `@login_required`, making it visible to unauthenticated users; now restricted
  like the rest of the app. [#34]
- **Self-service "mot de passe oublié" flow** — added Django's `PasswordResetView`/
  `PasswordResetDoneView` (project templates, reusing the `password_reset_confirm` URL
  name) so a user who forgets their password can request a new link themselves instead
  of relying on staff re-running the bulk account tool.
- **Restrict access to uploaded media files** — `/media/<path>` was served with no
  authentication check (`famille_busson/urls.py`), so `Person.profile_photo`,
  `Chalet.photo`, and blog `Attachment` files stayed readable by anyone with the URL.
  Added an authenticated serve view gating access the same way every other view is
  gated.
- **Adopt `LoginRequiredMiddleware` as defense-in-depth** — Django's built-in middleware
  (5.1+) that requires an explicit `@login_not_required` opt-out on every public view,
  so a future new view can't silently repeat the home-page bug. Opted out
  `CustomLoginView`, `SignupView`, `healthz`, the root redirect, and the media serve
  view.

### Frontend / UX
- **Responsive design for mobile navigation** — replaced the always-visible custom
  `.sidebar` in `annuaire/templates/annuaire/base.html` with a Bootstrap 5 offcanvas
  pattern: vendored `bootstrap.bundle.min.js`, added a hamburger toggle below the `lg`
  breakpoint, added media queries to `main.css` so the desktop layout is unchanged above
  it. [#31]
- **Site favicon** — minimalistic SVG mountain-and-trees favicon, wired into
  `base.html` (`<link rel="icon">`). [#33]

### Annuaire — profile improvements
- **Address picker for a person's address** — autocomplete field in the profile
  create/update views using France's free BAN API (api-adresse.data.gouv.fr, no key
  required): user types, candidates are returned, selecting one saves a standard
  one-liner address format. [#32]

### Publications — future improvements
- **Multi-author picker** — generalized `person_picker.js` (`annuaire/static/js/`) from
  a single `document.querySelector` instance to `querySelectorAll`-based support for
  multiple instances, and extracted the duplicated picker markup (previously
  copy-pasted across 4 templates, including `BlogPostForm.authors`) into a shared
  template include.
- **Orphaned file cleanup** — Django doesn't delete files under `MEDIA_ROOT` when a row
  referencing them is deleted. Fixed for `Person.profile_photo`, `Chalet.photo`, and
  `publications.Attachment.file` via `annuaire/file_cleanup.py`'s
  `register_file_cleanup(model, *field_names)`, connected as `post_delete` + `pre_save`
  receivers.

## Backfilled 2026-08-16 (shipped before this file existed)

The entries below were already implemented and released prior to `docs/` being set up,
so they're grouped under a single backfill heading rather than per release version.
Going forward, new entries here will be grouped under the release version they shipped
in.

### High-priority features
- **Directory list / search view** — `VueListeAnnuaire`, `annuaire_list.html` template,
  `/annuaire/` URL, first/last name search bar.
- **Sidebar navigation** — updated with the real URLs (Directory, PSV Chalets); the
  Publications section was removed from it.
- **Chalets** — `VueListeChalets` + `VueDetailChalet`, `chalet_list.html` and
  `chalet_detail.html` templates, `/chalets/` and `/chalets/<pk>/` URLs.
- **PSV presences** — `VueAjouterPresence`, `VueModifierPresence`,
  `VueSupprimerPresence`, `FormPresencePSV` form, `presence_form.html` template.
- **Homepage** — rebuilt as an extensible tile grid: directory tile (6 most recently
  added profiles), chalets tile. Structure ready for new tiles.

### Bugs fixed
- **Misused `HttpResponseForbidden`**:
  - `SignupView.form_valid()` — replaced with `messages.error` + `form_invalid`.
  - `VueEditionProfil.get_object()` — replaced with `raise PermissionDenied`.

### Bootstrap 4 → Bootstrap 5 migration
`crispy_forms` was configured with the `crispy_bootstrap4` pack while the project
targets Bootstrap 5.
- Replaced `crispy-bootstrap4` with `crispy-bootstrap5`.
- Updated `INSTALLED_APPS` (`crispy_bootstrap4` → `crispy_bootstrap5`).
- Updated `CRISPY_TEMPLATE_PACK = 'bootstrap5'`.
- Updated templates for Bootstrap-4-only classes/structures (e.g. `form-row` → `row`,
  `custom-select` → `form-select`).

### Cleanup
- Removed the 5 debug `print()` calls from `views.py`.
- Removed the unused `from django.contrib.auth.models import User` import from
  `forms.py`.

### Static files management
- Removed `STATICFILES_DIRS` pointing at a non-existent `static/images/` folder — the
  `annuaire` app's static files are auto-discovered via `AppDirectoriesFinder`.
- Removed the `<script src="js/bootstrap.min.js">` tag, which loaded a non-existent
  file; no Bootstrap 5 JS component (`data-bs-*`) is used in the templates.

### Tests
Full test suite in place under `annuaire/tests/`:
- `test_views_auth.py` — account creation, authentication.
- `test_views_profile.py` — profile editing restricted to its owner.
- `test_views_chalets.py` — chalets, presences, AJAX person search.
- `test_views_staff.py` — bulk account creation.
- `test_views_password.py` — forced password-change middleware.

Shared fixtures in `conftest.py`. CI on push via `.github/workflows/tests.yml`.
