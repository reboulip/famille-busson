# Roadmap Archive

Roadmap items that have shipped to production. Moved here from `ROADMAP.md` at release
time (see the `/release` skill), so `ROADMAP.md` only ever shows pending work.

## v0.8.0

### Carte
- **Person search in Carte** — select a person, center the map on their address. [#75]
- **Multiple members at the same address** — show all members sharing an address
  instead of just one (split marker / cluster with names+photos on click). [#68]

### Adresses
- **Worldwide address support** — extended the BAN-only address autocomplete
  (`address_picker.js`, `annuaire/forms.py`) with a Photon fallback so non-French
  addresses can be entered and geocoded. [#73]
- **Dropped `Chalet.gps_coordinates` free-text field** — removed the field, its form
  usage, and its display on `chalet_detail.html`, with a migration. [#63]

### Profil
- **Editable notification/subscription preferences** — exposed the
  profile-creation-time notification checkboxes in the profile edit form so they can be
  changed afterward. [#71]

### Authentification
- **Magic Link login** — passwordless email login reusing the existing one-time-link
  primitive (`_build_password_reset_url()`, `annuaire/views.py`) and configured email
  delivery, pointed at `login()` instead of the password-reset flow. Preserves the
  closed-signup guard (`Account` only links an existing `Person` by email, never
  auto-provisioned from the link). [#74]

## v0.7.0

### Profil et authentification
- **Password show/hide toggle on every password form** — extended the existing
  `password_toggle.js` (previously login-only) to `signup.html`,
  `password_reset_confirm.html` and `password_change_forced.html`. Also fixed a latent
  bug where the toggle's DOM wrapping broke Bootstrap's `.invalid-feedback` sibling
  selector, hiding field-level validation errors on these three forms. [#64]

### Généalogie — arbre interactif
- **Default to the biggest branch** — the bare `/annuaire/genealogie/` route now always
  centers on the family tree's largest connected branch, instead of the viewer's own
  profile. [#67]
- **Sort tree children by age** — siblings render oldest-to-youngest within each couple's
  children (server-side, unknown birth dates sorted last). [#61]

### Navigation
- **Reworded the GitHub feedback link** — "Signaler un bug" became "Signaler un bug ou
  proposer une évolution", inviting feature suggestions alongside bug reports. [#66]

### Généalogie — enfants sans compte
- **Accountless profiles with ownership** — any member can create a `Person` profile
  with no linked `Account` (e.g. for a child), behind a warning that this path is only
  for people who shouldn't get site access. The creator becomes an "owner" of the
  profile via a new `Person.owners` self-referential relation, restricted to
  accountless profiles, and can edit it (including relations) like their own; deletion
  stays admin-only. A new `can_edit_person()` guard in `annuaire/views.py` centralizes
  what were three separate ownership checks. [#60]
- **First-login redirect to an existing profile** — when an `Account` is created for
  someone who already has an accountless `Person` profile (auto-linked by email via the
  existing signal), the forced first-connection flow now lands on that profile's edit
  page instead of the profile-creation form. [#60]
- **Claim an existing profile during onboarding** — an authenticated account with no
  linked profile (a staff-created account, or a fiche with a missing/stale email) can
  self-service search accountless profiles from the profile-creation page and instantly
  link one, no approval step. Deliberately kept off the public signup form — the signup
  email-match check is the site's only signup gate, and exposing the same search there
  would have replaced it. Surfaced during Phase 2 sprint planning, no GH issue.
- Also hardened `link_account_to_person` against `Person.email` not being unique
  (previously an unhandled `MultipleObjectsReturned` was reachable once accountless
  profiles made duplicate emails possible), and owners are now cleared — not just
  permission-gated — the moment a profile gets its own `Account`, closing a stale-
  ownership path via `Person.account`'s `on_delete=SET_NULL`.

## v0.6.0

### Chalets en libre-service
- **Open chalet creation to all accounts** — chalet creation was staff-only; any
  authenticated account can now create a chalet, is auto-assigned as an owner, and can
  add further owners at creation time via the existing person-picker component. [#48]
  [#52]
- **Chalet address picker and GPS coordinates** — the person address BAN API picker is
  now reused for the chalet address field, capturing and storing GPS coordinates the
  same way. [#54]
- **Chalets on the Carte view** — extended the carte's avatar-marker approach to chalet
  markers. [#54]
- **Populate the home page Chalets card** — was empty even when chalets and presences
  existed; now populated the same way as the other home page cards. [#55]

### Carte
- **Fixed missing profile pictures on the carte view** — markers rendered correctly but
  profile pictures didn't. [#49]

### Profil et authentification
- **Line breaks between contact info types** — the annuaire profile display now breaks
  to a new line between each contact info type (email, phone, etc.), including on
  mobile. [#47]
- **Show/hide password toggle at login** — lets a user reveal the password they just
  typed on the login form for verification. [#50]

### Navigation
- **Link to GitHub issues from the site** — added a sidebar link so members can report
  bugs directly. [#51]
- **Home page link in the navigation bar** — there was previously no way back to the
  home page from elsewhere on the site. [#56]

### Généalogie — arbre interactif
- **Fixed genealogy view rendering/UX bugs** — search results rendered black-on-black;
  empty parent nodes showed a confusing "ADD" placeholder; edges between nodes were
  missing; selecting a node to show the detail panel de-centered the tree; and node
  labels didn't show the full name. [#59]
- **Dropped `Person.gender`** — investigation confirmed the family tree works without it
  (family-chart only used it cosmetically); removed the field, migration, form field,
  and family-chart payload key, replacing the lost card color cue with a
  generation-depth CSS accent. [#59]

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
