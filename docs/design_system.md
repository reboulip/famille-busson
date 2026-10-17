# Design system — Alpenglow / Nightfall

How the site is styled, and the rules to follow when you add a page.

The original design work (reasons, contrast measurements, mockups) is in
[`design/web/SPEC.md`](https://github.com/reboulip/famille-busson/blob/main/design/web/SPEC.md).
That folder was only used for review. **This page describes what is actually in the
site.**

## 1. Where things live

| File | What it holds |
|---|---|
| `annuaire/static/css/tokens.css` | The colour and font variables (`--fb-*`) for both palettes, and the fonts. |
| `annuaire/static/css/components.css` | The shared components (`.fb-*`). No colour is written directly here. |
| `annuaire/static/css/main.css` | Page-specific styles, and fixes for the external libraries (map, family tree, PDF viewer). |
| `annuaire/templatetags/icons.py` | The icons — `{% icon "mail" %}`. |
| `annuaire/templates/annuaire/_ridge.html` | The mountain ridge drawing. |
| `annuaire/templates/annuaire/_empty.html` | The shared "nothing here" block. |
| `annuaire/templates/annuaire/base.html` | The page layout for logged-in users (side menu, theme switch). |
| `annuaire/templates/annuaire/base_threshold.html` | The page layout for logged-out users (no side menu). |
| `annuaire/static/fonts/` | The Bitter and Karla fonts, hosted on the site itself. |

**The order of the stylesheets matters**, and a test checks it:

```
bootstrap.css → tokens.css → components.css → {vendor_css} → main.css
```

`tokens.css` connects Bootstrap's own variables to ours. So standard Bootstrap
components (buttons, alerts, tables, forms…) use our colours automatically. `main.css`
comes last because it must override the external libraries' styles.

## 2. Colour

There are two palettes: **Alpenglow** (light) and **Nightfall** (dark). They use the
same variable names with different values.

**Never write a colour code (like `#9C4A22`) directly.** It breaks the dark palette.
Always use a `--fb-*` variable.

The rule that is easy to get wrong:

- `--fb-alpenglow` has too little contrast for text. **Never use it for text.** Use it
  for decoration: focus outlines, the active menu marker, hover borders.
- `--fb-ember` is used for all coloured text and for the main button.
- In the dark palette, the bright ember is readable, so it takes both roles.

Status colours (success, warning, error) only appear as a thin bar on the left. The
status text itself is always in the normal text colour. This keeps every alert
readable in both palettes.

Full contrast table: `design/web/SPEC.md` §3.2.

**Staff can change `--fb-ember` and `--fb-alpenglow`** in the site settings
(`/annuaire/configuration/`). The site checks the contrast of the chosen colours. See
[`site_config.md`](site_config.md#theme-and-brand-colours-phase-153).

## 3. Theme switching

The `data-bs-theme` attribute on `<html>` sets light or dark mode. The site uses, in
this order: the user's choice (saved in the browser), then the system setting, then
light mode.

A small script inside `<head>` applies the saved choice before the page is drawn.
Otherwise the page would flash in the wrong colours first. The switch button is in
`annuaire/static/js/theme_toggle.js`.

## 4. Typography

Two fonts: Bitter (titles) and Karla (body text). Before they load, the browser uses
the same fallback fonts as the emails.

⚠️ **Font files are checked when the static files are collected.** If you rename or
move a font file without updating `tokens.css`, the production container will not
start. After any change in `annuaire/static/`, run:

```bash
DEBUG=False SECRET_KEY=x uv run python manage.py collectstatic --noinput
```

## 5. Adding a view

Find the type of page you are building (the list is in `design/web/SPEC.md` §7), then
follow these rules:

1. **Always start the page with `.fb-page-head`.** This header makes every page look
   like part of the same site.
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
2. **For an empty list, use the shared empty block.** Do not write your own "il n'y a
   rien ici":
   ```html
   {% url 'thing-create' as create_url %}
   {% include "annuaire/_empty.html" with title="Aucune chose" body="…" action_url=create_url action_label="Créer" %}
   ```
   For a page that new members see first, you can add a hint (`empty_hint`) and a
   second, quieter link (`empty_secondary_url` and `empty_secondary_label`):
   ```html
   {% url 'directory' as directory_url %}
   {% include "annuaire/_empty.html" with title="Aucun profil pour l'instant" empty_hint="Commencez par explorer qui fait partie de la famille." empty_secondary_url=directory_url empty_secondary_label="Voir l'annuaire" %}
   ```
   These options start with `empty_` so they do not clash with variables of the page
   that includes the block.
3. **Use `{% icon %}`, not emoji.** Emoji do not display on every system and do not
   follow the theme. Write `{% load icons %}`, then `{% icon "mail" size=16 %}`. An
   unknown icon name causes an error. To add an icon, add it to `_PATHS` in
   `annuaire/templatetags/icons.py` (24×24, outline style).
4. **People are round, places are rectangular.** Use `.fb-person-card` + `.fb-avatar`
   for people, and `.fb-place-card` + `.fb-place-card__media` for places. A place with
   no photo shows the ridge drawing (`.fb-place-placeholder`), never an emoji.
5. **Pages for logged-out visitors have no side menu.** They extend
   `base_threshold.html`. Pages about passwords and login links (reset, magic link,
   forced change) use a simpler header: they replace `{% block ridge %}` with
   `<div class="fb-horizon"></div>`.
6. **Never show a status with colour only.** Always add words (a label, a date…).
7. **Make the whole card clickable, not just its title.** Give the card
   `position: relative`, and add Bootstrap's `.stretched-link` class to the title link.
   No JavaScript is needed. Examples: `.fb-post-card` and `.category-tree__row`. Other
   links inside the card need `position: relative; z-index: 2` to stay clickable. A
   card with no link (for example, a locked category) gets no `.stretched-link`.
8. **To change a component for one page only, add a modifier class, and use both
   classes in the selector.** Write `.fb-post-card.fb-post-card--doc`, not just
   `.fb-post-card--doc`. This way, the override always wins over the base rule. Example:
   the document list uses `fb-post-card--doc` without changing the blog list.
9. **Page-specific rules for a shared component go in `main.css`, under a page
   class. Never put them in `components.css`.** Example: `.fb-record` is used by both
   the profile page and the place page. The profile's mobile changes use a
   `.profile-record` class that only the profile page has. A test checks that
   `components.css` never mentions it.
10. **To show only the icon of a button on small screens,** put the button text in a
    `<span class="…__label">`, hide that span on small screens, and copy the same text
    into the button's `aria-label` and `title`. The button keeps its name for screen
    readers. Example: the four buttons of the family tree toolbar
    (`.genealogie-toolbar__label`).

## 6. The ridge

`{% include "annuaire/_ridge.html" %}` draws the mountain ridge. There are three
versions: `full` (default: peaks, snow, pine trees), `plain` (no trees, for small
sizes) and `mark` (one ridge line only, for empty blocks).

It appears in exactly **three** places: the side menu logo, the header of logged-out
pages, and empty blocks. Do not add it anywhere else. `map_init.js` has its own copy
for places with no photo on the map. If you change the drawing, change both.

## 7. Things that will bite you

- **Fixes for external libraries go in `main.css`, not `components.css`.** They must
  load after the libraries' own styles.
- **Some CSS rules exist only to work around a bug in an external library.** Their
  comments explain why. Examples: `.fb-content { min-width: 0 }`,
  `.map-container { z-index: 0 }`, and `.f3 div.card`, which stops Bootstrap's `.card`
  style from applying to the family tree. If you move such a rule, keep its comment.
  Do not "clean it up".
- **Tests check some class names and some CSS rules.** Do not rename or change these
  without updating the tests: `contact-line`, `genealogie-toolbar` (must be the first
  class), `genealogie-detail d-none d-lg-block` (exact text),
  `markdown-editor-toolbar-btn`, `category-tree__row`, `fb-post-card--doc`,
  `fb-post-card__body`, `fb-post-card__meta`, `profile-record`,
  `profile-record__actions`, `profile-identity`, `profile-identity--pinned`,
  `profile-identity-sentinel`, `genealogie-toolbar__label`, `fb-longform--full`.
- **`{# … #}` comments must fit on one line.** A comment on several lines shows up as
  text on the page. For longer comments, use `{% comment %}…{% endcomment %}`.
- **`.stretched-link` covers the nearest element that has a `position`.** Choose that
  element carefully. If it is too small, most of the card does nothing. If it is too
  big, links inside it stop working. The link with `.stretched-link` must **not** have
  a `position` itself. Also, text on the card cannot be selected. This is expected.
- **`position: sticky` does not work in a grid area that is only one row high.** The
  row takes the height of the sticky element, so there is no room to scroll. On mobile,
  the profile page uses a normal block layout for this reason, and the side column uses
  `display: contents`.
- **The tests' `_rule_body()` helper cannot read rules inside `@media` blocks.** For
  those rules, tests first extract the `@media` block (see `_mobile_block()` in
  `test_profile_mobile_rail.py`).
- **`vh` ignores the mobile browser's bottom bar,** so an element sized in `vh` can be
  hidden behind that bar. `dvh` follows the bar as it shows and hides. The family tree
  on mobile uses `height: 70vh` as a fallback, then `height: calc(100dvh - 13rem)`.
  `13rem` is an estimate of the space above the tree.
