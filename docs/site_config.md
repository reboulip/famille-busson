# Site configuration

Some settings of the site can be changed by staff, without touching the code: the site
name, the sender address for emails, the colours, the logo, and more. This lets other
families use the site under their own name. These settings are stored in the
`SiteConfig` model (in `annuaire/models.py`).

## The model

There is only ever one `SiteConfig` row, and it cannot be deleted.

| Field | Meaning |
|---|---|
| `site_name` | The site's name. Shown in the browser tab, on the home page, in the menu, and in emails. |
| `wordmark` | The name shown as the logo text in the menu and in emails. It can differ slightly from `site_name` (for example, with a non-breaking space). If empty, `site_name` is used. |
| `tagline` | A short tagline. Stored, but not shown anywhere yet. |
| `sender_address` | The sender address for all emails. If empty, `DEFAULT_FROM_EMAIL` is used (see [`deployment.md`](deployment.md#environment-variables)). |
| `feedback_url` | The target of the "Signaler un bug" link in the menu. If empty, the link is hidden. |
| `place_label_singular`, `place_label_plural` | The name used for houses in the site (for example "Maison"/"Maisons"). If empty: "Résidence"/"Résidences". |
| `timezone` | The time zone used to show dates and times on the site. |
| `default_language` | The language for visitors who have not chosen one (see [`i18n.md`](i18n.md)). |
| `theme` | The colour theme. There is only one today: `"alpenglow"`. |
| `brand_primary_light`, `brand_primary_dark` | Optional. The main colour (links, buttons), for light and dark mode. If empty, the theme's colour is used. |
| `brand_accent_light`, `brand_accent_dark` | Optional. The accent colour (lines, focus outlines), for light and dark mode. If empty, the theme's colour is used. |
| `logo` | Optional. The site logo. |
| `favicon` | Optional. The icon in the browser tab. If empty, the default icon is used. |
| `updated_at` | The date of the last change. Used so browsers load a new icon after a change. |

A test (`annuaire/tests/test_no_residual_branding.py`) checks that the name "Busson"
is not written directly in the code or templates. Everything must come from these
settings.

## Reading it: `get_site_config()`

In code, always read the settings with `get_site_config()` (in
`annuaire/site_config.py`). Never query `SiteConfig` directly.

- If no row exists yet, it returns default values. It never creates a row.
- It keeps the result in the cache for 5 minutes. The cache is cleared when the settings
  are saved, so changes show at once.

## Where it's exposed

- **In templates:** the settings are available everywhere as `site_config`.
- **Time zone:** each web request uses the time zone from the settings. Background jobs
  and management commands use `TIME_ZONE` from the environment instead (see
  [`deployment.md`](deployment.md)).

## Branding: where the fields are actually consumed (Phase 15.2)

- **Pages:** the browser tab title, the logo text, the menu and the home page title
  come from `site_name` and `wordmark`.
- **Emails:** they use `site_name`, `wordmark` and `sender_address`. The password
  reset and magic link emails are built by Django, so they receive these values in a
  different way. See [`emails.md`](emails.md).
- **Calendar feed:** the `.ics` file also contains the site name.

## Theme and brand colours (Phase 15.3)

The themes are defined in `annuaire/theming.py`. There is only one today,
`"alpenglow"`, which matches the site's design (see
[`design_system.md`](design_system.md)). You can add more themes there later.

When staff choose a colour, the site checks it:

- **Format:** it must be a valid hex colour code (like `#9C4A22`).
- **Contrast:** it must be readable on the theme's backgrounds. The main colour is used
  for text, so it needs a contrast of at least 4.5:1. The accent colour is used for
  decoration, so it needs at least 3:1.
- **Exception:** the theme's own default colour is always accepted.
- An empty field keeps the theme's colour.

The chosen colours are added to every page as a small `<style>` block. If no colour is
changed, no block is added.

## Public branding assets: `/branding/<kind>`

The logo and the icon must show on the login page, before the visitor is logged in. But
uploaded files normally require login. So the logo and icon are served from a special
public address: `/branding/logo` and `/branding/favicon`. Only these two files can be
reached this way. See [`permissions.md`](permissions.md).

## Editing it

Staff edit the settings on the "Configuration" page (`/annuaire/configuration/`),
linked from the Administration section of the menu. The page works even before any row
exists: the first save creates it. The logo and icon are limited to 2 MB each.

The command `manage.py bootstrap_site` can also create the settings when you install a
new site. It does nothing if settings already exist, so it never overwrites changes
made on the page. See [`deployment.md`](deployment.md#one-time-setup).

Changes to the settings are recorded in the [audit log](audit.md), except the logo and
icon (they are files). When the logo or icon is replaced or deleted, the old file is
removed from disk.

## First-run seeding

When `SiteConfig` was added, a migration (`annuaire/migrations/0023_siteconfig_seed.py`)
filled it with "Famille Busson", but only on a site that already had accounts. A new
installation starts with empty settings. Fill them in with `bootstrap_site` or on the
"Configuration" page.
