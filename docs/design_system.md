# Design system — Alpenglow / Nightfall

How the site is styled, and the rules to follow when adding a view.

The design pass this implements — rationale, contrast measurements, the per-view
archetype table and the mockups — lives in [`design/web/SPEC.md`](https://github.com/reboulip/famille-busson/blob/main/design/web/SPEC.md).
That folder is a throwaway review artifact, not wired into Django; **this page is the
reference for the shipped system.**

## 1. Where things live

| File | What it holds |
|---|---|
| `annuaire/static/css/tokens.css` | The `--fb-*` tokens (both palettes), the Bootstrap 5.3 bridge, and the `@font-face` rules. |
| `annuaire/static/css/components.css` | Every shared component (`.fb-*`). Nothing here hardcodes a colour. |
| `annuaire/static/css/main.css` | Per-feature CSS and the leaflet / family-chart / pdf.js vendor overrides. |
| `annuaire/templatetags/icons.py` | The inline SVG icon set — `{% icon "mail" %}`. |
| `annuaire/templates/annuaire/_ridge.html` | The ridge mark. |
| `annuaire/templates/annuaire/_empty.html` | The shared empty state. |
| `annuaire/templates/annuaire/base.html` | The app shell (sidebar, nav, theme script). |
| `annuaire/templates/annuaire/base_threshold.html` | The logged-out shell (no sidebar). |
| `annuaire/static/fonts/` | Bitter + Karla, self-hosted (latin + latin-ext subsets). |

**Stylesheet load order is load-bearing** and asserted by
`test_stylesheets_load_tokens_and_components_after_bootstrap_and_main_last`:

```
bootstrap.css → tokens.css → components.css → {vendor_css} → main.css
```

`tokens.css` re-points Bootstrap's own `--bs-*` variables at the `--fb-*` tokens, so
stock Bootstrap components (`.btn`, `.alert`, `.table`, `.form-control`, `.nav`,
crispy-forms output…) inherit the palette without a per-component override. `main.css`
is last because most of what is left in it exists to beat a *vendor* stylesheet.

## 2. Colour

Two named palettes, carried over from the email system: **Alpenglow** (day) and
**Nightfall** (night over the valley). Same token names, different values.

**Never write a literal hex value.** It silently breaks Nightfall. Use `--fb-*`.

The one rule that is easy to get wrong:

- `--fb-alpenglow` is **2.98:1** on `--fb-card` — it is *never* text. Use it for the
  eaves stub, focus rings, the active-nav marker, card hover borders and button hover.
- `--fb-ember` is **5.90:1** — it carries every coloured word and fills the primary
  button.
- In Nightfall the roles collapse: the bright ember is the readable one (6.28:1) and
  takes over both.

Status colours are only ever the 3px left bar; **status text is always `--fb-ink` on a
tinted ground**, so every alert is AA by construction in both palettes.

Full contrast table: `design/web/SPEC.md` §3.2.

## 3. Theme switching

`data-bs-theme` on `<html>` drives both Bootstrap's dark theme and the `--fb-*`
overrides. Resolution order: explicit choice (localStorage `fb-theme`) →
`prefers-color-scheme` → light.

The stored choice is applied by a small **inline** script in `<head>`, before the
stylesheets paint — an external file would flash the wrong palette first. The toggle
button itself is `annuaire/static/js/theme_toggle.js`.

## 4. Typography

Bitter (display) + Karla (body), self-hosted as variable woff2. The fallback stacks are
byte-identical to the email system's (`Georgia, 'Noto Serif', serif` /
`'Trebuchet MS', Verdana, Helvetica, Arial, sans-serif`), so with `font-display: swap`
the first paint of any page *is* the email's typography.

⚠️ **`@font-face` `url()` references are validated at collectstatic time** by
WhiteNoise's `CompressedManifestStaticFilesStorage`. Renaming or moving a font file
without updating `tokens.css` kills the container at boot. Run the build-sanity check
after touching `annuaire/static/`:

```bash
DEBUG=False SECRET_KEY=x uv run python manage.py collectstatic --noinput
```

## 5. Adding a view

Pick the archetype it belongs to (the full table is in `design/web/SPEC.md` §7), then:

1. **Always** open with `.fb-page-head` — the eaves rule is what makes every view read
   as one product.
   ```html
   <div class="fb-page-head">
       <div class="fb-page-head__titles">
           <p class="fb-eyebrow">Section</p>
           <h1>Titre</h1>
           <p class="fb-page-head__lede">Une ligne d'explication.</p>
       </div>
       <div class="fb-page-head__actions">…</div>
   </div>
   ```
2. **Never hand-write "il n'y a rien ici".** Use the shared empty state:
   ```html
   {% url 'thing-create' as create_url %}
   {% include "annuaire/_empty.html" with title="Aucune chose" body="…" action_url=create_url action_label="Créer" %}
   ```
3. **Use `{% icon %}`, not emoji.** Emoji render as tofu boxes wherever the system has
   no emoji font and cannot follow the theme. `{% load icons %}` then
   `{% icon "mail" size=16 %}`. An unknown name raises rather than rendering nothing.
   Add new glyphs to `_PATHS` in `annuaire/templatetags/icons.py` — 24×24, stroked,
   `stroke-width` comes from the wrapper.
4. **People are round, places are rectangular.** `.fb-person-card` + `.fb-avatar` vs
   `.fb-place-card` + `.fb-place-card__media`. A place with no photo gets the ridge
   (`.fb-place-placeholder`), never an emoji.
5. **Threshold pages get no sidebar.** Anything a visitor sees before they are logged
   in extends `base_threshold.html`. Credential flows (password reset, magic link,
   forced change) override `{% block ridge %}` with `<div class="fb-horizon"></div>` —
   the restrained treatment, mirroring how the emails split full vs. restrained.
6. **Status is never carried by colour alone** — pair the treatment with words (a chip,
   a label, a date range).
7. **Card-style list items should be clickable across their whole surface**, not just
   the title. Give the card `position: relative` and put Bootstrap's `.stretched-link`
   on the existing title/name `<a>` — its `::after` overlay stretches to fill the
   nearest positioned ancestor, so no JS is needed. `.fb-post-card` (blog posts,
   documents) and `.category-tree__row` (category tree rows) both do this. Any other
   link inside the card that must stay independently clickable (an author link, a
   category link in the `.fb-meta` line) needs `position: relative; z-index: 2` so it
   sits above the overlay. An item with no link (e.g. a locked category) gets no
   `.stretched-link` and stays inert.
8. **Give a one-consumer layout variant a modifier class, paired with the base class
   in the selector** — `.fb-post-card.fb-post-card--doc`, not a single-class override.
   Both classes give the override the same specificity as the base `.fb-post-card`
   rule, so which one wins is decided by source order (the modifier comes after) —
   a single-class selector would instead win or lose unpredictably as the stylesheet
   grows. The documents list row (`fb-post-card--doc`) is the current example: it
   re-flows `.fb-post-card__body` and `.fb-post-card__meta` into a row without
   touching the publications feed's `.fb-post-card`.
9. **Page-specific rules on a component shared by more than one page go in `main.css`
   under a page-scoped class, never in `components.css`.** `.fb-record` is shared by
   the profile and chalet detail pages; the profile's mobile sticky-identity condensing
   hangs off a `.profile-record` class added only in `personne_detail.html`, so chalet
   detail's layout is untouched. A test (`test_the_shared_record_component_is_not_
   restyled_for_the_profile_page`) asserts `components.css` never mentions the
   page-scoped class at all.
10. **To collapse a button's caption to icon-only on small screens**, wrap the caption
    text in `<span class="…__label">`, hide that span with CSS below the breakpoint, and
    mirror the same text into `aria-label` and `title` on the button — so the control
    keeps its accessible name once the text is not painted, and (in this codebase) the
    text stays in the DOM for any source-text test that asserts on the rendered label
    string. The genealogy toolbar's three buttons (`genealogie-export`,
    `genealogie-export-image`, `genealogie-fullscreen`) are the current example, using
    `.genealogie-toolbar__label`.

## 6. The ridge

`{% include "annuaire/_ridge.html" %}` — variants `full` (default: peaks, snowcap,
pines), `plain` (no pines, for small sizes) and `mark` (near ridge only, for the
empty-state watermark).

It appears in exactly **three** places: the sidebar brand block, the threshold card
header, and empty states. A ridge on every page would be wallpaper. `map_init.js`
carries its own inline copy for photoless chalet markers — keep the two silhouettes in
sync if either changes.

## 7. Things that will bite you

- **Vendor overrides belong in `main.css`, not `components.css`** — they have to win
  against stylesheets that load after `components.css`.
- **Several CSS rules exist to defeat a specific vendor bug** and say so at length in
  their comments (`.fb-content { min-width: 0 }`, `.map-container { z-index: 0 }`,
  `align-items: safe center` on the viewer stage, the two-class zoom specificity fix,
  the family-chart label width pair, `.f3 div.card` neutralizing Bootstrap's `.card`
  component from painting a square behind family-chart's identically-named node
  wrapper — `background`/`border`/`border-radius` only, `display` is deliberately left
  alone). Port the comment with the rule; do not "tidy" them.
- **Some class names are pinned by tests**: `contact-line`, `genealogie-toolbar` (must
  come first in its class attribute), `genealogie-detail d-none d-lg-block` (exact
  string), `markdown-editor-toolbar-btn` (exact attribute order), `category-tree__row`,
  `fb-post-card--doc`, `fb-post-card__body`, `fb-post-card__meta`, `profile-record`,
  `profile-record__actions`, `profile-identity`, `profile-identity--pinned`,
  `profile-identity-sentinel`, `genealogie-toolbar__label`. `.fb-post-card` and
  `.fb-post-card .fb-meta a` (components.css), `.f3 div.card` (main.css), and the
  `.fb-post-card--doc`/`.profile-record`/`.profile-identity`/`.genealogie-toolbar__label`
  rules also carry source-text-tested declarations, not just names — see below.
- **`{# … #}` comments are single-line only.** A multi-line one renders as visible text
  on the page. Use `{% comment %}…{% endcomment %}`.
- **`.stretched-link`'s overlay fills the nearest `position`ed ancestor** — get that
  ancestor's scope wrong and the overlay swallows either too little (nothing happens on
  most of the card) or too much (nested interactive content goes dead). The category
  tree row wraps only the row itself, deliberately excluding the child `<ul>`, so child
  rows stay independently clickable. Anything meant to stay clickable above the overlay
  needs `position: relative; z-index: 2` of its own — and the `.stretched-link` element
  itself must **not** be positioned, or the overlay re-anchors to it instead of the
  card. The technique also makes body text over the card unselectable; that's an
  accepted trade-off, not a bug to fix.
- **A `position: sticky` child has no room to travel inside a grid area that only
  spans one row** — the row auto-sizes to the sticky element's own height, so it
  never scrolls past it. `.fb-record`'s mobile layout collapses to a single-column
  grid, so the sticky rule on `.profile-identity` was inert there until the mobile
  media query first set `.profile-record`/its rail to `display: block`, giving the
  identity card a normal block ancestor it can travel — and stick — within.
- **The source-text tests' `_rule_body()` helper cannot see inside an `@media`
  block** — its regex finds the first top-level occurrence of a selector, so a rule
  that only exists inside a media query (the mobile sticky/condensing rules in
  `main.css`) has to be sliced out by brace-balance first (see `_mobile_block()` in
  `test_profile_mobile_rail.py`) and asserted on as a raw substring, not through
  `_rule_body()`.
- **`vh` resolves against the *largest* viewport** — as if a mobile browser's
  collapsible bottom bar were already hidden — so a `vh`-sized element's bottom edge
  sits underneath that bar while it's showing on screen. `dvh` (dynamic viewport
  height) tracks the bar as it shows and hides. `.genealogie-container`'s mobile rule
  (in `main.css`'s `@media (max-width: 991.98px)` block for the genealogy section)
  declares `height: 70vh;` first — kept as the fallback for browsers without `dvh`
  support — then overrides it with `height: calc(100dvh - 13rem);`; the `13rem` is an
  estimate of the page chrome above the chart (top bar, page head, toolbar), not a
  measured value, and the base rule's `min-height: 320px` still floors it.
