# Site configuration

Phase 15's first step toward making famille-busson deployable as a
generically-branded site for other families, not just the Busson family: a
`SiteConfig` singleton (`annuaire/models.py`) holding the site's identity and
a few runtime settings, editable by staff instead of hardcoded.

## The model

`SiteConfig` is a singleton — `save()` forces `self.pk = 1`, and `delete()`
raises `ValueError` unconditionally, so there is always at most one row and it
can never be removed.

| Field | Type | Notes |
|---|---|---|
| `site_name` | `CharField` | The site's display name. Read across templates (browser-tab titles, the homepage headline, the nav's brand section label) and emails (`email_context()`, the two Django-stock `extra_email_context` properties, the iCal `PRODID` line, `account_setup()`'s subject). |
| `wordmark` | `CharField` | Kept separate from `site_name`, not derived from it — the wordmark can carry its own typographic treatment (e.g. a non-breaking space between words). Falls back to `site_name` wherever it's read (templates and emails alike) when left blank. Read by the sidebar/topbar brand link, `base.html`/`base_threshold.html`, and every email's `_wordmark.html` partial. |
| `tagline` | `CharField` | Stored but not yet read anywhere. |
| `sender_address` | `EmailField` | Used as the `from_email` for every outgoing message (`email_utils.build_message()`), falling back to `settings.DEFAULT_FROM_EMAIL` when blank. |
| `feedback_url` | `URLField` | Controls the "Signaler un bug" nav link in `base.html`/`base_threshold.html`: shown only when set, hidden entirely otherwise. |
| `timezone` | `CharField` | Defaults to `settings.TIME_ZONE`. Activated per-request by `SiteTimezoneMiddleware` (see below). |
| `default_language` | `CharField` | Choices drawn live from `settings.LANGUAGES`. Read by `annuaire.i18n.resolve_language()` (Phase 15.5) as the site-wide fallback when a visitor has no saved `Account.language` and no `django_language` cookie yet — see [`i18n.md`](i18n.md). |
| `theme` | `CharField` | Names an entry in the `annuaire.theming.THEMES` registry (see "Theme and brand colours" below). Only choice today: `"alpenglow"`. |
| `brand_primary_light`, `brand_primary_dark` | `CharField` | Hex colour, optional. Overrides the theme's primary (link/button) role for light/dark mode respectively. Blank keeps the theme default. |
| `brand_accent_light`, `brand_accent_dark` | `CharField` | Hex colour, optional. Overrides the theme's accent (rules/focus-ring) role for light/dark mode respectively. Blank keeps the theme default. |
| `logo` | `ImageField` | Optional. Served publicly at `/branding/logo` (see below), not through `/media/`. |
| `favicon` | `ImageField` | Optional. Served publicly at `/branding/favicon`; referenced by `base.html`/`base_threshold.html`'s `<link rel="icon">`, cache-busted with `?v={{ site_config.updated_at|date:'U' }}`, falling back to the static `favicon.svg` when unset. |
| `updated_at` | `DateTimeField` | `auto_now`. Only used as the cache-busting value for the favicon URL above — not otherwise exposed. |

Phase 15.1 landed the model, its read path, and the staff edit screen with
every field still inert. Phase 15.2 wired `site_name`, `wordmark`,
`sender_address` and `feedback_url` into every template and outgoing email
that used to hardcode "Famille Busson"/"les Busson"/"la famille Busson" or
the repo's own GitHub issue tracker link. Phase 15.3 added the configurable
theme/brand-colour/logo/favicon fields above. Phase 15.4 made every
user-facing string translatable (see [`i18n.md`](i18n.md)) but did not yet
wire `default_language` into that machinery. Phase 15.5 (this page's latest
update) closed that gap — `default_language` now feeds
`annuaire.i18n.resolve_language()`'s precedence chain. **`tagline` remains
the only field still stored but unused.**

## Reading it: `get_site_config()`

`annuaire/site_config.py`'s `get_site_config()` is the only supported read
path — never query `SiteConfig` directly in a read context. It:

- Never creates a row: if none exists yet, it returns an unsaved,
  defaults-only `SiteConfig()` instance, so a plain GET can never trigger a
  write (no signal firing, no audit-log entry) just from reading the config.
- Caches the result under the key `"site_config"` for 300 seconds
  (`CACHE_TTL`). `annuaire/signals.py`'s `invalidate_site_config_cache`
  receiver clears that cache key on every `SiteConfig` `post_save`, so an edit
  is visible immediately rather than up to 5 minutes later.

It lives in its own module (not `models.py`) so `context_processors.py` and
`middleware.py` can import it without pulling in the whole models module
graph — `middleware.py` in particular imports it lazily, inside
`SiteTimezoneMiddleware.__call__`, because that module is loaded during
`django.setup()` before the app registry is ready.

## Where it's exposed

- **Every template:** the `site_config` context processor
  (`annuaire/context_processors.py`, registered in `TEMPLATES` in
  `config/settings.py`) puts the `SiteConfig` instance in every
  template's context under `site_config`.
- **Every request's active timezone:** `SiteTimezoneMiddleware`
  (`annuaire/middleware.py`, registered in `MIDDLEWARE` right after
  `SessionMiddleware`) calls `timezone.activate(ZoneInfo(...))` with
  `SiteConfig.timezone` at the start of the request and
  `timezone.deactivate()` afterwards. Since the field defaults to
  `settings.TIME_ZONE`, behaviour is unchanged until an admin actually edits
  it. Only affects the request/response cycle — management commands and
  background jobs still run under `settings.TIME_ZONE`.

## Branding: where the fields are actually consumed (Phase 15.2)

- **Templates:** every page's `{% block title %}` (login, signup, the magic-link
  and password-reset flows, `password_change_forced`), `base.html`'s and
  `base_threshold.html`'s `<title>`, brand `aria-label`, wordmark, and nav
  section label, and `home.html`'s headline all read `site_config.site_name`/
  `site_config.wordmark` from the context processor rather than a literal
  string. The "Signaler un bug" link in `base.html`/`base_threshold.html` is
  now wrapped in `{% if site_config.feedback_url %}` — it no longer
  unconditionally points at this repo's own GitHub issue tracker.
- **Emails:** `email_utils.email_context()` puts `site_name`/`wordmark` (the
  latter falling back to `site_name`) into the context shared by every
  `annuaire.emails` builder, and `build_message()`'s `from_email` prefers
  `SiteConfig.sender_address` over `settings.DEFAULT_FROM_EMAIL`. The email
  templates/text bodies and the shared `emails/_wordmark.html`/`_base.html`
  partials read `{{ site_name }}`/`{{ wordmark }}` from that context.
  `emails.account_setup()`'s non-reset subject line now interpolates
  `site_name` instead of a fixed string. `ical.render_ics()`'s `PRODID` line
  interpolates the configured (escaped) site name too, falling back to
  `"Site"` when blank.
- **The two Django-stock flows (password reset, magic link) are the one
  exception to `email_context()`:** `AccountPasswordResetView`/
  `MagicLinkRequestView` render through Django's own `PasswordResetView`
  machinery, which only accepts flat scalar context via
  `extra_email_context` — so on both views that attribute changed from a
  class attribute (evaluated once at import time, before any database
  existed) to a `@property` that re-reads `get_site_config()` on every
  request and returns `site_base_url`/`site_name`/`wordmark` directly. See
  [`emails.md`](emails.md) for the full email system.

## Theme and brand colours (Phase 15.3)

`annuaire/theming.py` defines a `Theme` dataclass and a `THEMES` registry —
today a single entry, `"alpenglow"`, matching the site's existing Alpenglow
design system (see [`design_system.md`](design_system.md)). Each `Theme`
carries the default primary/accent colours for light and dark mode, plus the
two fixed surface colours (card/raised-surface and page-background) staff
colour choices are contrast-checked against. This is a real seam for adding
more named themes later, not a single hardcoded palette — `SiteConfig.theme`
just names which registry entry is active.

`FormSiteConfig`'s `clean_*` methods for the four `brand_*` colour fields
validate:

- **Format:** must be a valid hex colour.
- **Contrast:** checked with `annuaire.contrast.contrast_ratio()` (WCAG 2.1
  relative-luminance math) against both of the active theme's surface
  colours. The primary (text) role requires `AA_TEXT = 4.5`; the accent
  (non-text — rules, focus rings) role requires `AA_NON_TEXT = 3.0`. A
  submitted colour failing its threshold against either surface is rejected.
- **One exception:** a submitted colour that exactly matches the active
  theme's own shipped default for that role always passes, even where that
  default's own ratio against a surface is marginal — the validation exists
  to stop a staff member from picking a colour *worse* than what already
  ships, not to retroactively re-litigate the shipped design.
- Leaving a colour field blank keeps the theme default and always passes.

`annuaire.theming.brand_css_overrides(config)` emits `:root`/dark-mode CSS
custom-property overrides for `--fb-ember`/`--fb-alpenglow` (the tokens
`design_system.md` documents), restricted to values that actually differ
from the active theme's defaults — it returns an empty string when nothing
is overridden, so an unconfigured install emits no override `<style>` block
at all and renders pixel-identical to before this wave. Exposed to every
template via the `brand_css` context processor
(`annuaire/context_processors.py`) as `brand_css_overrides`, and inlined
between `components.css` and `main.css` in `base.html`/`base_threshold.html`.

## Public branding assets: `/branding/<kind>`

`branding_asset` (`annuaire/views.py`, route name `branding-asset`,
`@login_not_required`) is the public counterpart to the login-gated
`/media/` route: the configured logo/favicon must render on the login page
itself, for a visitor with no session yet. `kind` is looked up against a
fixed `{"logo": ..., "favicon": ...}` mapping onto
`SiteConfig.logo`/`SiteConfig.favicon` only — 404 on anything else, so it
carries no path-traversal window into the rest of `MEDIA_ROOT`. See
[`permissions.md`](permissions.md) for the full public-surface list.

## Editing it

`SiteConfigUpdateView` (`annuaire/views.py`, route name `site-config`, URL
`/annuaire/configuration/`) is staff-only (`StaffRequiredMixin`; see
[`permissions.md`](permissions.md)). `get_object()` returns
`get_site_config()` rather than a plain `get_object_or_404` lookup, so the
edit form works even before any row exists — the first save creates it.
`FormSiteConfig` (`annuaire/forms.py`) exposes 14 of the 15 fields above —
everything except `updated_at`, which is `auto_now` and not user-editable —
across three fieldsets in `site_config_form.html`: identity, emails/feedback,
and (new this wave) "Marque" for theme/colours/logo/favicon. The form now
needs `enctype="multipart/form-data"` for the logo/favicon uploads.
Uploaded logo/favicon are capped at 2 MB. Linked from "Configuration" in the
staff-only Administration group of the main nav
(`annuaire/templates/annuaire/base.html`).

Changes are recorded in the audit log: `SiteConfig` is registered with
`register_audit()` in `annuaire/signals.py` for its 12 scalar fields (the
original seven, plus `theme` and the four `brand_*` colours) — see
[`audit.md`](audit.md). `logo`/`favicon` are deliberately excluded from that
allowlist (files, not diffable scalars); their lifecycle is instead handled
by `register_file_cleanup(SiteConfig, "logo", "favicon")`
(`annuaire/signals.py`), the same cleanup-on-delete/replace pattern used for
`Person.profile_photo`/`Chalet.photo` (see `CLAUDE.md` §5).

## First-run seeding

`annuaire/migrations/0023_siteconfig_seed.py` is a conditional data
migration: it seeds this deployment's current "Famille Busson" identity into
the new `SiteConfig` row, but only if `Account.objects.exists()` at migration
time. On this already-running deployment that condition is true, so the
migration ran with real data. A genuinely fresh install (no accounts yet)
gets an empty/generic `SiteConfig` instead, left for the first admin to fill
in via the edit screen above.
