# Roadmap Archive

Roadmap items that have shipped to production. Moved here from `ROADMAP.md` at release
time (see the `release-workflow` skill), so `ROADMAP.md` only ever shows pending work.

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
