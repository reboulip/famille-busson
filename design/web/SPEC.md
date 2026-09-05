# Web design spec — extending Alpenglow to the application

Design pass for the **site itself**, extending the visual system established for the
emails in [`../emails/SPEC.md`](../emails/SPEC.md).

**Nothing in this folder is wired into Django.** Same convention as `design/emails/`:
a throwaway spec + working mockups for review, outside `docs/` and outside any app's
`templates/` dir, before anything is built. `tokens.css` and `components.css` are
written as real, adoptable CSS rather than illustration — they are meant to be lifted
into `annuaire/static/css/` largely as-is when implementation starts.

## Files

| File | What it is |
|---|---|
| `SPEC.md` | This document |
| `tokens.css` | The token layer + the Bootstrap 5.3 bridge. Real, adoptable. |
| `components.css` | The component layer. Real, adoptable. |
| `shell.js` | **Mockup scaffolding only** — injects the sidebar so each mockup can show one archetype. Not for shipping. |
| `01-accueil.html` | Archetype A — hub |
| `02-collections.html` | Archetypes B (grid) and C (feed) |
| `03-details.html` | Archetypes D (record) and E (long-form) |
| `04-outils.html` | Archetype F — canvas tools |
| `05-formulaires.html` | Archetypes G (form), I (tabular), J (destructive confirm) |
| `06-seuil.html` | Archetype H — threshold / auth |

Open any mockup directly in a browser. The **◐ Nightfall** button at the bottom of the
sidebar (top-right on `06-seuil.html`) switches palettes. The webfonts 404 until they
are vendored — that is deliberate, and what you see is the Georgia/Trebuchet fallback,
i.e. exactly the email's typography.

---

## 1. Where the site stands today

Worth stating plainly, because it sets how much of this is *new design* versus *design
that was never written down*.

- **`main.css` is 1258 lines of per-feature CSS with no system underneath it.** No
  variables, no scale, no palette. Colours are typed literally at each site:
  `#0d6efd`, `#6c757d`, `#f8f9fa`, `#dee2e6`, `#e0e0e0`, `#f4f4f4`, `#333`, `#555`,
  `#666`, `#777`, `#888`. Spacing is ad-hoc (`4px`, `5px`, `6px`, `8px`, `10px`,
  `12px`, `15px`, `16px`, `20px`, `24px` all appear).
- **`body { font-family: 'Helvetica'; }`** — quoted, single family, no fallback stack.
  There is no Helvetica on Linux or Android, so on most devices this silently resolves
  to whatever the browser's default happens to be.
- **Two whole apps have no CSS at all.** `publications` and `documents` ship zero
  stylesheets. `.blogpost-card`, `.blogpost-detail`, `.comment`, `.comment-header`,
  `.document-card`, `.category-tree`, `.badge-bc`, `.badge-normal`, `.attachment-image`
  and `.blogpost-list` are written in the templates and matched by **nothing**. Those
  pages render as unstyled HTML flow.
- **The sidebar has no active state.** You cannot tell which page you are on.
- **Logged-out pages render the full app sidebar**, every link in it bouncing back to
  the login form.
- **There is no brand system** beyond `annuaire/static/favicon.svg` — a mountain with a
  snowcap and two pines. That icon is the only pre-existing asset, and this pass builds
  outward from it.
- Assorted specifics: `.expandable-image` grows 100 px → 200 px over a **1 second**
  transition on hover, reflowing the page under the cursor; the 🏔️ emoji is the chalet
  photo placeholder and renders as a tofu box on any system without an emoji font
  (visible in the project's own `.shots/01-landing.png`); alert styling is split
  between a hand-rolled `.alert-error` and stock Bootstrap for the other three tags;
  roughly fifteen empty states are each hand-written as a bare `<p>Aucun…</p>`.

So: this is less "restyle a designed app" and more "give a working app its first design".

## 2. Direction

The emails committed to a direction: *light, warm, evocative of the Alps — a chalet,
not a corporate app*, in two named palettes, **Alpenglow** (day) and **Nightfall**
(night over the valley). That direction carries over unchanged. What changes is the
medium's constraints, and therefore the technique:

| | Email | Web |
|---|---|---|
| Ridge motif | Bordered-`<div>` triangles + MSO fallback | Inline SVG |
| Typography | Georgia / Trebuchet (webfonts unreliable) | Bitter / Karla, **falling back to Georgia / Trebuchet** |
| Dark mode | `prefers-color-scheme` only | `prefers-color-scheme` + an explicit toggle |
| Layout | One 600 px column | Shell + ten view archetypes |

The through-line is deliberate: **a member who gets the birthday email, taps the button,
and lands on the profile page should not experience a change of brand.** Same palette,
same ridge, same eaves rule, same wordmark, same warmth.

### Three signature devices

Everything else is ordinary good layout. These three are what make it *this* product:

1. **The eaves rule.** In the emails, a 2 px ink rule sits directly over a 1 px
   hairline beneath the ridge — a nod to the fascia trim under a chalet roof edge. On
   the web that double rule becomes the universal page-header device: a 56 × 3 px
   alpenglow stub above a full-width hairline (`.fb-page-head`). It goes on *every*
   view. One class is what makes fifty-five templates read as one product.

2. **The ridge.** Three uneven peaks (real skylines are not symmetric), slate-mist
   behind, spruce in front, a zigzag snowcap on the tallest — the same zigzag as
   `favicon.svg` — and the favicon's two pines planted at the base. It appears in
   exactly **three** places: the sidebar brand block, the threshold card header, and as
   a faint watermark in empty states. A ridge on every page would be wallpaper; three
   placements make it a signature.

3. **The wordmark.** "Famille Busson" in the display serif, uppercase, letter-spaced
   `0.2em`, set small into the sky band like a signpost. Identical treatment to the
   email header.

---

## 3. Palette

### 3.1 Tokens

Every hex that also appears in the email spec is byte-identical to it. Full definitions
in `tokens.css`; this is the map of what each token is *for*.

**Alpenglow (light)**

| Token | Hex | Role | From email spec? |
|---|---|---|---|
| `--fb-parchment` | `#F6EEE0` | Page ground | ✅ `parchment` |
| `--fb-card` | `#FFFAF0` | Raised surface — cards, panels, inputs | ✅ `card` |
| `--fb-panel` | `#EFE3D0` | Recessed surface — sidebar, table heads | ➕ new |
| `--fb-sky` | `#F3D9B1` | Sky band behind the ridge | ✅ (used in the mockups, absent from the table) |
| `--fb-border` | `#E6D8C3` | Hairlines, card borders | ✅ `border` |
| `--fb-border-strong` | `#D8C4A6` | Input borders, dashed rules | ➕ new |
| `--fb-ink` | `#3A2C1E` | Primary text | ✅ `ink` |
| `--fb-bark` | `#7A6650` | Secondary text | ✅ `bark` |
| `--fb-alpenglow` | `#D9793F` | Rules, focus ring, active marker, hover | ✅ `alpenglow` |
| `--fb-ember` | `#9C4A22` | **Link text, primary button fill** | ✅ `ember` (role changed — see 3.2) |
| `--fb-ember-soft` | `#F6E3D4` | Accent chip ground | ➕ new |
| `--fb-spruce` | `#4B5D3F` | Near ridge; doubles as success | ✅ `spruce` |
| `--fb-slate-mist` | `#9FB0AE` | Far ridge; empty-state watermark | ✅ `slate-mist` |
| `--fb-snowcap` | `#FBF6EC` | Peak highlight | ✅ `snowcap` |
| `--fb-gold` | `#D9A441` | Celebration accent — portrait ring on hover, "Busson connection" | ✅ `gold` |
| `--fb-danger` | `#A83A28` | Destructive | ➕ new |

Nightfall mirrors all of the above from the email spec's dark table (`night`,
`card-dark`, `ivory`, `dust`, `ember-bright`, `moon`, `pine-dark`, `starlight`,
`gold-dark`, `border-dark`), plus the same new tokens re-derived for dark.

### 3.2 One deliberate divergence from the email spec — and why

The email spec assigns `alpenglow` (`#D9793F`) to "CTA buttons, links, heading rule".
On the web that fails WCAG AA for text, and unlike email, the web is where AA is
actually assessed. Measured:

| Pair | Ratio | Verdict |
|---|---|---|
| `alpenglow` `#D9793F` on `card` `#FFFAF0` | **2.98:1** | ✗ fails AA for text (passes 3:1 for non-text UI) |
| `card` `#FFFAF0` on `alpenglow` fill | **2.98:1** | ✗ fails AA — a filled button label |
| `ink` `#3A2C1E` on `alpenglow` fill | **4.33:1** | ✗ just short of 4.5 |
| **`ember` `#9C4A22` on `card`** | **5.90:1** | ✓ AA |
| **`card` on `ember` fill** | **5.90:1** | ✓ AA |
| `bark` `#7A6650` on `card` | 5.25:1 | ✓ AA (safe for body copy, still reserved for meta) |
| `spruce` `#4B5D3F` on `card` | 6.87:1 | ✓ AA |
| `danger` `#A83A28` on `card` | 6.12:1 | ✓ AA |
| `ivory` on `card-dark` (Nightfall) | 12.7:1 | ✓ AAA |
| `ember-bright` `#E2914E` on `card-dark` | 6.28:1 | ✓ AA |

So the roles split by contrast rather than by name:

- **Alpenglow is never text.** It is the eaves stub, the focus ring, the active-nav
  marker, the card hover border, the post-card type bar, and the button hover state.
- **Ember carries every coloured word** and fills the primary button.

Note the asymmetry this produces, which is real and intentional: in **Nightfall** the
bright ember *is* the readable one (6.28:1), so it takes over both roles and the deep
ember drops out entirely. Same role, opposite direction, both AA.

Alerts sidestep the question altogether: **status text is always `--fb-ink` on a tinted
ground**, and the status colour appears only as a 3 px left bar. Every alert is AA by
construction, in both palettes.

### 3.3 The Bootstrap bridge

Bootstrap 5.3.3 is already vendored and exposes nearly everything it paints as a
`--bs-*` custom property. `tokens.css` re-points those at the `--fb-*` tokens, so
`.btn`, `.alert`, `.badge`, `.table`, `.form-control`, `.nav`, `.offcanvas`,
`.dropdown` and `.pagination` inherit the palette **without a per-component override
and without editing `bootstrap.css`**. Crispy Forms output is re-skinned for free by
the same mechanism.

This matters for effort: most of the 55 templates need no markup change to stop looking
like stock Bootstrap. The archetype work below is then about layout, not repainting.

---

## 4. Typography

| Role | Face | Size | Weight / leading |
|---|---|---|---|
| Display (hub only) | Bitter | `clamp(2rem, 1.55rem + 1.5vw, 2.75rem)` | 700 / 1.08, `-0.02em` |
| h1 | Bitter | 2 rem | 700 / 1.2 |
| Long-form h1 | Bitter | 2.25 rem | 700 / 1.1 |
| h2 | Bitter | 1.375 rem | 600 / 1.35 |
| h3 | Bitter | 1.0625 rem | 600 / 1.4 |
| Body | Karla | 1 rem | 400 / 1.65 |
| Long-form body | Karla | 1.0625 rem | 400 / 1.75 |
| Meta / caption / help | Karla | 0.8125 rem | 400 / 1.5, `--fb-bark` |
| Eyebrow (section label) | Karla | 0.75 rem | 700, uppercase, `0.12em` |
| Wordmark | Bitter | 0.75 rem | 700, uppercase, `0.2em` |

**Bitter + Karla are the pairing the email spec named as "aspirational"** — the look
most email recipients never get, because Outlook's Word engine ignores `@font-face`.
The web app has no such constraint, so this is where that pairing actually lands.

Two decisions attached to it:

- **Self-hosted, not Google Fonts.** Matches how the project already vendors leaflet,
  d3, pdf.js and family-chart, and production serves through WhiteNoise with no
  external CDN in play. Two variable woff2 files under
  `annuaire/static/fonts/`, ~35–45 KB each.
- **The fallback stacks are byte-identical to the email's.** `Bitter → Georgia, 'Noto
  Serif', 'Droid Serif', serif`; `Karla → 'Trebuchet MS', Verdana, Helvetica, Arial,
  sans-serif`. With `font-display: swap`, the *first paint* of every page is the email's
  typography, replaced when the woff2 lands. A font that fails to load degrades to the
  email, not to nothing.

⚠️ **`collectstatic` gate.** `CLAUDE.md` §9 documents that WhiteNoise's
`CompressedManifestStaticFilesStorage` validates every CSS `url()` at collectstatic
time, and that a vendored asset with a missing referenced file kills the container at
boot. `@font-face` `src: url(...)` is exactly such a reference. The build-sanity check
(`DEBUG=False SECRET_KEY=x uv run python manage.py collectstatic --noinput`) is
**mandatory** on the commit that adds the fonts.

---

## 5. Space, shape, motion

- **Space:** 4 px base — `--fb-sp-1..8` = 4, 8, 12, 16, 24, 32, 48, 64 px. Nothing
  off-scale.
- **Radius:** 6 px controls · 10 px cards/canvases · 16 px threshold card · pill for chips.
- **Shadow:** warm, tinted with ink, never neutral black.
  `--fb-shadow-1/2/3` = resting card / hover + floating panel / modal-weight.
- **Motion:** 120 ms hover, 200 ms panels, one shared easing curve, all inside a
  `prefers-reduced-motion` guard. This replaces the 1 s hover-grow on
  `.expandable-image`, which reflows the page under the cursor — the portrait becomes a
  fixed 150 px medallion, and enlargement moves to the existing image viewer.
- **Focus:** every interactive element gets `outline: 2px solid var(--fb-alpenglow)`
  with a 2 px offset. Today only the genealogy autocomplete has any focus style.

---

## 6. The shell

**Sidebar** — `--fb-panel` wood ground, hairline right edge, sticky full height.

- **Brand block** at the top: sky band, the wordmark set as a signpost, the SVG ridge,
  closed by the eaves line. This is the email header, transplanted.
- **Identity pill** directly beneath: avatar + name + "Mon profil", in a bordered card.
- **Nav**: eyebrow section labels, 3 px transparent left border on every item that
  turns `--fb-alpenglow` with a `--fb-card` ground for `aria-current="page"`. This is
  the missing active state.
- **Foot**, pinned: Nightfall toggle + logout, above a hairline.
- **Mobile**: the naked floating toggle button becomes a proper sticky top bar carrying
  the sky band, the eaves rule and the wordmark; the panel itself moves into the
  existing Bootstrap offcanvas unchanged.

**Content column** — `max-width: 76rem` for grids and tools, `38rem` for long-form.
Keeps `min-width: 0` (load-bearing: it is what stops a zoomed document or wide table
from scrolling the whole page sideways, see the comment in `main.css`).

---

## 7. The ten archetypes

The requested "same style everywhere, with variations adapted to each view" is this
table. Every one of the 55 templates lands in exactly one archetype.

| | Archetype | Views | The variation |
|---|---|---|---|
| **A** | **Hub** | `home` | The only view that earns the full ridge in the content column — it is the front door and has no subject of its own. Display-size wordmark, a live one-line summary of the family's week, then content-height tiles (today they stretch to the row and leave large voids). |
| **B** | **Collection grid** | `annuaire_list`, `_annuaire_results`, `chalet_list` | Card grid + filter toolbar. **People are round, places are rectangular** — today chalets reuse `.personne-card` and are round too, with the tofu-prone 🏔️ as the fallback. A chalet with no photo gets the ridge instead. |
| **C** | **Collection feed** | `blogpost_list`, `_blogpost_card`, `document_list`, `_document_card`, `_document_results`, `category_list`, `_category_tree_node`, `category_detail` | No medallion — a post has no portrait. A 3 px left bar codes the type (alpenglow = normale, gold = Busson connection), title in Bitter, excerpt clamped to two lines. The category tree gets indent guides and a dashed lock chip. **These templates currently have no CSS whatsoever.** |
| **D** | **Record detail** | `personne_detail`, `chalet_detail` | Two columns: a sticky identity rail (portrait, aligned contact list, stacked actions) and a content column. **Relations become named cards** instead of 1.5 em anonymous thumbnails. Presence tables move to the content column. |
| **E** | **Long-form** | `blogpost_detail`, `document_detail` (text part), `help_magic_link`, `magic_link_confirm` | Narrows to a 38 rem measure at 1.0625 rem / 1.75. Attachments as a gallery grid; comments as avatar-disc rows; the comment composer on a recessed parchment ground so it reads as "your turn". |
| **F** | **Canvas tool** | `carte`, `genealogie`, the viewer inside `document_detail` | The chrome recedes. Toolbar welded to the canvas (`--attached`: shared radius, no seam) so the two read as one instrument. Detail/aside panels become floating shadowed cards. Only vendor colours change — the OSM basemap is not retinted. |
| **G** | **Form** | `update_form`, `profile_create`, `profile_claim`, `person_create`, `person_owners_form`, `person_relations_form`, `chalet_form`, `chalet_owners_form`, `presence_form`, `group_form`, `group_members_form`, `blogpost_form`, `document_form`, `category_form`, `password_change_forced` | Each `<fieldset>` becomes a card and its `<legend>` a real underlined section title, so a long form is a readable stack rather than one undifferentiated crispy block. Explicit label / help / error grammar. |
| **H** | **Threshold** | `login`, `signup`, `magic_link_request`, `magic_link_sent`, `password_reset`, `password_reset_done`, `password_reset_confirm` | **No sidebar.** Needs a second base template, `annuaire/base_threshold.html`. The card is the transactional email's card 1:1. Full ridge for login/signup; the restrained flat horizon for the credential flows, exactly as the emails split them. |
| **I** | **Tabular** | `group_list`, `bulk_account_create`, presence tables | Panel-ground header row with eyebrow labels, hairline separators only (drop `table-bordered`), row hover tint, status as chips rather than Bootstrap contextual row classes. |
| **J** | **Destructive confirm** | `blogpost_confirm_delete`, `comment_confirm_delete`, `document_confirm_delete`, `category_confirm_delete`, `group_confirm_delete` | Card with a red left edge; consequences enumerated on a tinted ground instead of buried in a sentence. The destructive button is **filled**, cancel is a ghost link — today both are `btn-outline-*` of identical visual weight. |

**Partials and widgets** (`_person_picker`, `_presence_calendar`, `_profile_edit_actions`,
`_profile_photo_size_check`, `widgets/markdown_editor`) are not archetypes — they inherit
the chip, input, toolbar and button components and appear inside whichever archetype
hosts them. The presence calendar's bar colours retune to `--fb-bark` (past),
`--fb-spruce` (current) and `--fb-ember` (future).

### Shared components introduced

`.fb-page-head` · `.fb-section-head` · `.fb-card` (+ `--link` hover) · `.fb-avatar` ·
`.fb-person-card` · `.fb-place-card` · `.fb-post-card` · `.fb-chip` · `.fb-toolbar`
(+ `--attached`) · `.fb-empty` · `.fb-alert` · `.fb-btn` · `.fb-table` · `.fb-contact` ·
`.fb-relation` · `.fb-comment` · `.fb-composer` · `.fb-gallery` · `.fb-canvas` ·
`.fb-fieldset` / `.fb-field` · `.fb-threshold` · `.fb-confirm` · `.fb-ridge` · `.fb-eaves` ·
`.fb-wordmark`.

**`.fb-empty` is worth calling out**: roughly fifteen bare `<p>Aucun…</p>` become one
component with the ridge watermark, a title, an explanation, and the relevant primary
action in reach. It is the cheapest single change with the widest reach.

---

## 8. Accessibility

- Every colour pair in §3.2 measured; the four that fail are excluded from text use by
  construction, in both palettes.
- Status is never carried by colour alone — alerts have a label, chips have words
  ("Jamais connecté", "Échec d'envoi"), locked categories carry a lock glyph *and* a
  dashed border *and* the group name, deceased profiles get a date range chip alongside
  the greyscale treatment.
- Focus ring on everything interactive (§5).
- `text-wrap: balance` on headings; long French names wrap rather than clip.
- The reading measure is capped at 38 rem for prose — today body text runs the full
  window width.
- `prefers-reduced-motion` honoured globally.

## 9. Nightfall on the web

`data-bs-theme` on `<html>` drives both Bootstrap's own dark theme and the `--fb-*`
overrides — one attribute, both systems. Resolution order: explicit user choice
(localStorage) → `prefers-color-scheme` → light.

To avoid a flash of the wrong palette on a server-rendered page, the stored choice must
be applied by a small **inline** script in `<head>`, before the stylesheet paints:

```html
<script>
  try {
    var t = localStorage.getItem('fb-theme');
    if (t) document.documentElement.setAttribute('data-bs-theme', t);
  } catch (e) {}
</script>
```

Nightfall is fully specified and costs nothing extra in `tokens.css`, but it is a
distinct increment — see phase 4 below. Everything before it works in Alpenglow alone.

---

## 10. Implementation notes and constraints

Things the build should know before starting.

- **Tests assert on literal class strings.** These are pinned and must survive any
  markup change:
  - `annuaire/tests/test_views_family_tree.py` — `class="genealogie-toolbar`, and
    exactly `id="genealogie-detail" class="genealogie-detail d-none d-lg-block"`.
  - `annuaire/tests/test_widgets_markdown_editor.py` — counts
    `type="button" class="markdown-editor-toolbar-btn"` **eight times**, attribute order
    included.
  - `annuaire/tests/test_views_profile.py` — counts `class="contact-line`.

  So the genealogy toolbar/detail, the markdown toolbar buttons and the profile contact
  lines must keep their existing class names (add new ones alongside, don't replace),
  or the tests get updated in the same commit as a deliberate act.
- **Load-bearing CSS comments in `main.css` must survive the migration.** Several rules
  exist to defeat a specific vendor bug and say so at length: `.content { min-width: 0 }`
  (#111), `.map-container { z-index: 0 }`, `.map-marker-avatar img { width: 100% !important }`,
  the `.f3 div.card-image-circle div.card-label` width/max-width pair, the
  `align-items: safe center` on the viewer stage (#109), and the
  `.document-file-preview-image.document-viewer-zoomable--zoomed` two-class specificity
  fix. Port the rules *and* their comments; do not "clean them up".
- **`collectstatic` must be run** on the font commit and on any commit touching
  `annuaire/static/` (§4, and `CLAUDE.md` §9).
- **`.fb-page-head` used as a bare rule.** In the long-form mockups an empty
  `.fb-page-head` stands in for a horizontal rule. Implementation should give that its
  own `.fb-rule` class rather than shipping an empty div.
- **`color-mix()`** is used for hover tints and the pine fill. Baseline-supported in all
  current browsers; if a fallback is wanted, the affected properties are few enough to
  precede with a flat value.
- **`shell.js` is not for shipping.** Its markup belongs in `annuaire/base.html`,
  rendered server-side, with `aria-current` set from the resolved URL name.

## 11. Suggested phasing

Ordered so each phase is independently shippable and visibly better than the last.

1. **Foundation.** `tokens.css` + the Bootstrap bridge + fonts + `.fb-page-head` on
   every view, `main.css` rewritten onto tokens with no layout change. The whole app
   changes palette and typography; no template restructuring. Highest ratio of visible
   change to risk.
2. **The unstyled apps.** Archetypes C, E, I, J — `publications` and `documents` get a
   design for the first time, plus `.fb-empty` everywhere and the alert unification.
   This is where the largest absolute improvement is.
3. **Restructures.** Archetypes A, B, D, G, H — hub tiles, the grid card split, the
   person/chalet two-column record, form fieldsets, and the `base_threshold.html`
   split. The only phase that moves markup around much.
4. **Nightfall + canvas polish.** Archetype F's vendor re-skins and the dark palette
   with its toggle and no-flash script.

Phases 1–2 alone would already close most of the gap.

---

## 12. Open questions

1. **Emoji as iconography.** The contact rows (📧 ☎️ 🏠 🎂 ✝), the chalet placeholder
   (🏔️), attachments (📎 🖼️), download (📥) and fullscreen (⛶) are all emoji today.
   They are warm and cost nothing, but they tofu on systems with no emoji font — and
   the argument I used to replace the chalet placeholder applies equally to the rest.
   **Recommendation: a six-glyph inline SVG set** for the contact rows and toolbars,
   keeping emoji only where it is decorative rather than load-bearing. The mockups
   still show emoji so you can judge the trade before it is made.
2. **Webfonts at all.** Vendoring Bitter + Karla adds ~80 KB and a `collectstatic`
   hazard. The alternative — shipping the Georgia/Trebuchet stack alone — is the exact
   look every email recipient already gets and is genuinely decent. Worth an explicit
   yes/no.
3. **Is Nightfall wanted on the site?** The emails have it because clients force-invert
   messages and an explicit dark mode is the defence. The site has no equivalent
   pressure; it is purely a nicety. Fully specified either way, and phase 4 can simply
   be dropped.
4. **The hub's one-line summary** ("22 profils, 5 chalets, 3 personnes à Praz-sur-Verre
   cette semaine") is the only place this pass invents *content* rather than
   presentation — same flag the email spec raised for the new-post excerpt. It needs a
   small amount of view work. Keep or drop?
5. **`.expandable-image`'s hover-grow.** Replacing it with a fixed medallion removes a
   feature, small as it is. Confirm that is wanted before it goes.
