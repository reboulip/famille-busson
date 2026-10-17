# Bulletins familiaux — draft spec: PDF → JSON package → web page

Design pass for importing the scanned family bulletins into `publications`, written
while prototyping on the first issue (BC n°17, April 1995), 2026-09-27.

**Nothing in this folder is wired into Django.** Same convention as `design/web/`: a
spec plus a working prototype for review, outside `docs/` and outside any app's
`templates/` dir, before anything is built. The templates, the stylesheet and the
template helpers are written to be lifted into `publications/` largely as-is. Roadmap:
Phase 19 (item 19.1).

**Real family data never goes in git.** The transcribed issue (draft JSON, package,
rendered preview) contains names, a postal address, a phone number and private family
news. It lives in the git-ignored `.claude/tmp/bulletins/`, which the prototype scripts
use as their data folder.

## Files

| Path | What it is |
|---|---|
| `SPEC.md` | This document |
| `bulletin.schema.json` | JSON Schema (draft 2020-12), `schema_version` 0.2: the package contract |
| `prototype/build_package.py` | Agent draft JSON + source PDF → package (crops, page previews, hashes, typography) |
| `prototype/validate.py` | Schema check + integrity checks → VALID / INVALID. To become the importer's validator |
| `prototype/render.py` | Packages → static preview of the site, using the real site CSS and Django's template engine |
| `prototype/export.py` | Preview folder + zip that opens offline (`file://`), for review on another machine |
| `prototype/bulletin_tags.py` | Template helpers: escaped inline rendering, French typography, event badge… (→ `publications/templatetags/`) |
| `prototype/bulletin.css` | The bulletin stylesheet, tokens only (→ `publications/static/css/` or a `components.css` section) |
| `prototype/bulletin.js` | Carousel buttons and counter over a CSS scroll-snap track; the carousels work without it (→ `publications/static/js/`, or merged with `publication_attachments.js`) |
| `prototype/make_demo.py` | Generates `prototype/fixtures/demo-001/`: a made-up issue (drawn pictures, neutral text) exercising what BC n°17 lacks. Deterministic: the importer's future test fixture |
| `prototype/fixtures/demo-001/` | That synthetic package: docked picture with a printed caption, a gallery, two consecutive figures, added captions, an illegible word, an aside |
| `prototype/templates/` | `publications/bulletin_detail.html`, `bulletin_list.html`, one partial per block type; `preview_shell.html` + `ridge.html` stand in for `annuaire/base.html` |
| `prototype/fonts/` | Caveat (variable woff2, latin + latin-ext) and its OFL licence |
| `prototype/shoot.cjs` | Full-page screenshots with the system Chromium (via the `run-famille-busson` skill's Playwright) |

## 0. Goal

Dozens of scanned family newsletters ("Busson's Connection", abbreviated *BC*), one PDF
per issue, need to become web pages in `publications` that always render the same way on
desktop and mobile.

Pipeline:

1. **PDF → package**: an AI agent turns one PDF into a *bulletin package*, a folder
   holding `bulletin.json` (validated against `bulletin.schema.json`) plus the pictures,
   each with a unique ID.
2. **Package → website**: the package is uploaded into `publications`. The site stores
   the JSON as the source of truth and renders it with fixed templates, so the design can
   change later without re-processing any PDF.

## 1. Observations from the first sample (BC n°17, April 1995)

- The PDF is a pure scan: a Xerox WorkCentre 7830 scan made in 2014, 9 A4 pages, **no
  text layer and no fonts**. Text extraction returns nothing, so the agent has to
  *read* the pages visually. OCR is no fallback either: there is no tesseract binary in
  the dev container, and OCR on handwriting would be poor anyway.
- It uses Mixed Raster Content (MRC) compression. Each page is a ~100 dpi 8-bit
  greyscale background plus a ~200 dpi 1-bit JBIG2 foreground mask (the "ink").
  Consequences:
  - Always **render the page and crop**; never extract the raw embedded images. A raw
    image is just one layer, e.g. a mask without its background.
  - 200 dpi is the useful ceiling for crops and zooms. Rendering higher adds nothing.
  - Photos sit in the 100 dpi layer, and dark areas can be flattened to pure black by
    the mask. The photo on p.4 is effectively a silhouette, and no processing will bring
    the detail back.
- Every page has a `/Rotate 270` flag. PyMuPDF and the Read tool both honour it. The
  agent must work in *displayed* (rotated) page coordinates.
- The content mixes **typed text** (two columns, bold and italic, sub-headings), **neat
  handwriting** (French cursive), **tables** (the godparent list), a **photo**, a
  **flyer** (an invitation with display lettering), **signatures**, and a few
  **marginalia** (a pencil note added later on p.1).
- The file name encodes the metadata: `BC <issue number> <editor abbreviation> <MM-YYYY>.pdf`.
  The abbreviation is the editor-in-chief's first name.

## 2. Decisions taken while prototyping

### 2.1 Package format

```
<doc-id>/
  bulletin.json            # validated against bulletin.schema.json (v0.2)
  images/<image-id>.<ext>  # jpg (photos, page previews) or png (ink, masthead, documents)
```

- **Document id** = `<series code>-<zero-padded number>` (`bc-017`). It is unique across
  the corpus and prefixes every image id, so image ids are globally unique without UUIDs,
  stay readable, and are **stable across re-runs**. That enables idempotent re-imports:
  update in place instead of duplicating.
- **Image file name = image id** (`images/<id>.<ext>`). The validator enforces this.
- Each image records `width`/`height` (so the renderer reserves its space and the layout
  doesn't jump), `sha256` (integrity on upload), and `source.page` + `source.bbox` +
  `source.dpi` (provenance, and a re-crop is always possible).
- **bbox coordinates** are fractions of the *displayed* page, origin top-left. They
  don't depend on resolution, and they survive `/Rotate` flags.
- **Page previews are part of the package**: one `kind: page` image per PDF page at
  150 dpi, about 2 MB for 9 pages. The site then needs no PDF rendering to show "the
  original document".
- The original PDF is identified (`source.file_name`, `source.sha256`) but **not copied**
  into the package. *Open question:* should the import also attach the PDF itself, for
  example as a `publications.Attachment`?

### 2.2 Schema design (JSON Schema draft 2020-12, `schema_version: "0.2"`)

- **Semantics, not layout.** No columns, fonts, positions or alignment. The website owns
  presentation, which is what makes every issue render the same way.
- Top level: document identity (`id`, `title`, `series`, `issue`, `date` with an ISO
  partial date plus the printed text, `credits` as printed), `summary` (generated),
  `source` (PDF + pages), `images[]`, `articles[]`, `marginalia[]`, `processing`
  (agent, model, conventions, review status, notes for reviewers).
- **Articles** form a flat list in reading order. `rubric` holds the recurring section
  name as printed, and consecutive articles with the same rubric are grouped by the
  renderer. An article needs a `title` or a `rubric` (or both). `script` is
  typed/handwritten/mixed. `pages` records provenance.
- **Blocks** use a closed set of 13 types. 11 are "simple": paragraph, heading
  (level 1–2, relative to the article), list, quote, separator, figure, gallery, table,
  event, signature, address. 2 are containers holding simple blocks only (no recursion):
  `news_item` (the "Name: news" entries of family news) and `aside` (an insert box).
  `gallery` and `aside` are not exercised by BC 17; the synthetic `demo-001` fixture
  covers them.
- **Captions: every picture can have one.** A `figure` has `caption` (inline text) and
  `caption_editorial` (boolean). A `gallery` is a list of `items`, each
  `{image, caption?, caption_editorial?}`, plus an optional caption for the whole
  group. `caption_editorial: true` means the caption was written during transcription
  because the original prints none. The renderer marks such captions, so a reader never
  mistakes them for the original. Captions belong to the *placement* (figure, gallery
  item), not to the image entry.
- **Changes in 0.2** (from 0.1): `gallery.images` (a list of ids) became `gallery.items`
  (objects with a caption each); `caption_editorial` was added to figures, gallery items
  and galleries; `images[].caption` was removed.
- **Inline text** is either a plain string or an array of runs. A run is a string, a
  styled run (`bold`/`italic`/`underline`/`strike`/`superscript`), an `uncertain`
  reading (with optional alternatives), an `illegible` span (an **inline image** of the
  word), or a `break`. There is no Markdown and no HTML: the renderer escapes every
  string, so imported content cannot inject markup.
- **`event` block**: structured facts (dates as printed plus ISO start/end, place name
  and locality, organizer). The prose stays in paragraphs. It gives a consistent
  "save the date" card and could later feed the `events` app or the calendar.
- **`address` block**: postal/contact details are *typed*, so the renderer can apply a
  visibility policy. See §4.
- `additionalProperties: false` everywhere: an agent typo fails validation instead of
  silently disappearing.

### 2.3 Transcription conventions ("faithful-v1")

- **Words as written**: original spelling, grammar, capitalization and punctuation are
  kept, including mistakes ("Systhèmes", "nous avait concocté", "Bartogli (XVIIè)").
  No `[sic]`.
- **Handwriting**: missing accents are restored when haste obviously dropped them
  ("Debut" → "Début"). Line breaks are ignored unless meaningful (then an inline
  `break`). Underlining is kept only where it marks something (e.g. "Groupe"). The
  underlined names that open news entries become `news_item.subject` instead.
- **Typography** is normalized by the build tool, not by the agent: `'` → `’`. English
  double quotes become `“ ”`; French `« »` are kept. The renderer adds no-break spaces
  before `: ; ! ? »` for display only; the data keeps plain spaces.
- **Presentational emphasis is dropped**: italics or bold covering a whole article
  (e.g. p.8, all italic) are not transcribed. Emphasis inside text is.
- **Uncertain words** → an `uncertain` span, plus a `processing.notes` warning.
  **Unreadable handwriting** → an image: an `illegible` inline span for a word, a
  figure/signature image for a passage. Signatures are always images.
- **Reading order** follows the physical order, merging continuations across pages and
  columns. The only exception: an annex explicitly announced by an article joins that
  article. In BC 17, the p.9 table joins the p.8 article "Liste des parrains et
  marraines", as its table block.
- **Marginalia** (notes added to the paper later, stamps) go in `marginalia[]`, outside
  the content flow.
- **Graphic pieces** (a flyer's display lettering, the masthead) get a figure *in
  addition to* their transcription, to preserve the look of the original.
- **Inferred data** (e.g. a year missing from a date) is allowed only in structured
  fields (`event.dates[].start`) and must be explained in `processing.notes`.
- **Captions**: a printed caption is transcribed as the caption. When the original
  prints none, the agent writes a short, factual caption (what or where, never a guess
  about who), with `caption_editorial: true`. Provenance ("p. 4") is added by the
  renderer, and `alt` still describes the image for screen readers.
- **Picture groups**: several pictures presented together with little or no text (a
  photo page, a collage) are transcribed as one `gallery`. Short texts that belong to
  the pictures become their captions. Pictures separated by real text stay separate
  `figure` blocks, placed where they appear in the reading order.

### 2.4 Tooling that turned out to be needed (the agent's toolbox)

1. **Page renderer / zoomer**: render any page region at up to 200 dpi, greyscale, with
   rotation applied. Transcription quality depends on it: handwriting and a 40-row table
   need zoomed strips, and the full-page view is not enough.
2. **`prototype/build_package.py`**: the agent writes a *draft* JSON with each image's
   page + bbox + alt. The tool renders and crops (per-kind dpi and format; ink crops are
   trimmed to content; near-white paper is pushed to white), fills
   `file`/`media_type`/`width`/`height`/`sha256`, hashes the PDF, and applies the
   typography pass. The agent never handles pixels.
3. **`prototype/validate.py`**: the JSON Schema check plus the semantic checks JSON
   Schema can't express: unique ids, id prefixes, references resolved, file hash and
   dimensions match, one preview per page, bbox rules, table rows as wide as the header,
   event start ≤ end, notes pointing at real articles. Reports stats (block types,
   uncertain and illegible counts). Tested against 9 deliberately broken copies: all
   rejected.
   - *To improve:* `oneOf` errors on inline runs are vague ("is not valid under any of
     the given schemas"). Agents fix their output from these messages, so the validator
     should explain the failing branch (e.g. with `jsonschema.exceptions.best_match`
     plus custom hints).
4. Dependencies: PyMuPDF and Pillow are already in the project venv. `jsonschema` is
   **not**, so the prototype runs it with `uv run --with jsonschema`. The real feature
   needs `uv add jsonschema`.

## 3. Rendering: what the prototype settled

The renderer uses **Django templates**, so they can move almost as-is into
`publications/templates/publications/`. Every string goes through `escape()`. The
stylesheet uses the site's design tokens only, so Alpenglow and Nightfall work with no
extra code.

### 3.1 Layout: docked pictures, carousels, captions

The page **uses the whole screen width**: it opts out of the app's `76rem` content cap
(`.fb-content__inner:has(> .fb-bulletin)`) and centres a prose column on a page grid:

| Track | Width | Holds |
|---|---|---|
| `content` | `min(100%, 42rem)` (≈72 characters at 17 px) | the sections and articles: headings, prose, handwritten sheets, event cards, signatures, addresses, notes |
| `wide` | up to `72rem` | masthead, sommaire, draft banner, the page scans |

An article body is **one flow of text** (`display: flow-root`), so pictures can dock in
it. The free space on each side of the centred prose column (0 on a phone), computed
from container units `(100cqi − 42rem) / 2`, is what docked pictures, tables and
carousels may reach into. Handwritten sheets keep everything inside the sheet.

The renderer applies three rules, in `render.prepare_blocks`, so every issue lays out
the same way:

1. **A single picture docks right, and the text wraps around it.** The picture takes
   45% of the prose column plus up to `14rem` of the free right margin, never more than
   its own pixel width (`--natural-w`, set inline per picture), and never taller than
   `80vh`. The following paragraphs, headings and lists flow beside it, then continue
   at full width underneath. Boxes that must not run under a picture (event card,
   address, aside, news entries) are flex, grid or `flow-root` boxes, so they sit
   beside it, narrowed. Tables, carousels, separators and signatures clear it.
2. **A picture with no text after it is centred** (it may spread into the margins):
   a float with nothing beside it would leave a hole.
3. **Several pictures with no text between them form one carousel**, and so does a
   `gallery`. The carousel sits on the prose column plus both margins, one picture at a
   time, each with its own caption, plus the group caption if any.

- **Captions**: under every picture, one line: the caption, then the page it comes from
  ("· p. 4", or "· Extrait de la page 6" for an inserted document). A caption added
  during transcription is set in italics, with a tooltip and hidden text: "Légende
  ajoutée lors de la transcription".
- **Carousels** are a CSS scroll-snap track that works without JavaScript: swipe,
  trackpad, scrollbar, or arrow keys once focused. `bulletin.js` adds the
  previous/next buttons and the "2 / 5" counter (hidden until the script runs), and
  brings a targeted slide to the front.
- **The original document** is a carousel too, in its "strip" variant: a row of pages at
  a readable height, three visible at a time on a laptop. An article's "p. 6" link jumps
  to page 6 in the strip.
- **Masthead**: scan and titles side by side from `56rem`. **Sommaire**: two columns from
  `56rem`.
- **Narrow screens** (below `40rem`): nothing floats. Pictures stack at full width with
  their captions; carousels stay swipeable. Below `36rem`, news entries and tables
  switch to their stacked forms.
- Measured on BC 17 and demo-001: no horizontal overflow at 390, 1366 and 1920 px, in
  both themes. Carousel buttons, counter and keyboard were tested in Chromium.

### 3.2 Components

| Element | Treatment |
|---|---|
| Masthead | The scanned masthead (blended into the page, inverted in dark mode) next to: eyebrow "Bulletin familial", title `<series> n°<N>` in the display font, date, credits, summary, "Feuilleter l'original (N pages)" button |
| Draft banner | `fb-alert--info` while `processing.review.status == "draft"` |
| Sommaire | Card listing articles as "rubric / title ····· p. 4–5" with dotted leaders, anchored to each article |
| Rubric | The original's rounded, shadowed label box, redrawn in CSS (ink border and a 4 px offset shadow). It is the one visual nod to the paper bulletin, and it is identical across issues |
| Article header | Kicker (eyebrow), title (`h2` without rubric, `h3` under one), italic subtitle, byline, "p. N" link to the page scan, "Manuscrit" / "En partie manuscrit" chip |
| Handwritten article | Title in a handwriting font (**Caveat**); body on a "notebook sheet": card background plus a thin margin line. **Body text stays in the body font (Karla) for readability** |
| news_item | Two-column row: name in Caveat (ember colour) on the left, news on the right; stacked when narrow; dashed rule between entries |
| event | Card with a tear-off-calendar badge ("NOV. / 11–12 / 1995", computed from ISO dates), one calendar-icon line per date, a pin line for the place, organizer |
| quote | Italic, alpenglow left border (same as the site's long-form blockquote) |
| separator | Short centred alpenglow stub, echoing the short hand-drawn rules of the original |
| figure | Docked right with the text wrapping around it, or centred when no text follows (§3.1). Photo with border and shadow; `document` (flyer) as a slightly tilted paper print; ink crops (handwriting, signature) small and blended into the page |
| carousel | Render-time block for a gallery or consecutive pictures: panel with one picture at a time, per-picture captions, "‹ 2 / 5 ›" controls, group caption below |
| caption | The caption (printed: ink colour; added during transcription: italic, grey, marked for screen readers) followed by "· p. N" |
| signature | Right-aligned in the prose column: closing and name in Caveat when handwritten, role in small grey type, signature scan below |
| address | Centred panel headed "Coordonnées publiées en avril 1995": the date warns readers that the details are historical |
| table | The site's `fb-table`. `key` column narrow with tabular figures; the next column bold as the row label; row groups separated by a double rule; empty cells shown as "—" plus hidden "non renseigné". **When narrow, each row becomes a small record** ("<code> <first name>" / "Parrain : …" / "Marraine : …") |
| uncertain | Dotted alpenglow underline, superscript "?", tooltip plus hidden text "Lecture incertaine — autre lecture possible : …", keyboard-focusable |
| illegible | Inline crop of the scan at text height |
| Original document | A strip carousel of the page previews ("feuilleter"); each slide is `#page-N`, the target of the article "p. N" links, outlined with `:target`. Marginalia listed below |
| Transcription notes | Collapsible `<details>`: the notes, plus date, agent, model, conventions, status and schema version |
| Listing | One card per issue: first-page thumbnail, "Busson's Connection n°17", date · pages · editor, "Brouillon" chip, summary |
| French typography | No-break space inserted before `: ; ! ? »` and after `«` at render time |
| Dark mode | Ink crops get `invert + hue-rotate + screen` (light ink on dark paper); documents are dimmed (`brightness(.86)`) instead of inverted |

### 3.3 Implementation notes for the real feature

- **Full width**: the prototype widens the content area with
  `.fb-content__inner:has(> .fb-bulletin)`, in CSS only. The real page may prefer an
  explicit hook, e.g. a `{% block content_class %}` in `annuaire/base.html`.
- **Layout rules live in Python, not in the data**: grouping pictures into carousels
  and choosing dock or centre happen at render time (`prepare_blocks`). The package
  never says "float right", so the rules can change later without re-importing
  anything. Unit-test them on block sequences: figure + text, figure alone, figure +
  figure, gallery, figure + table.
- The per-picture width cap is an inline `style="--natural-w: 746px"`. The site has no
  CSP and already uses inline styles; revisit this if a CSP is added.
- Carousels: the site already has a carousel in `publication_attachments.js` (the
  attachment viewer). Either reuse it, or keep `bulletin.js` (~70 lines, no dependency).
- **Caveat must be self-hosted** (OFL licence), like Bitter and Karla: woff2 files in
  `annuaire/static/fonts/` plus `@font-face` rules. Production has no external CDN
  (WhiteNoise, CSP). Run the collectstatic sanity check afterwards (CLAUDE.md §9). The
  prototype already does this: variable woff2 from `@fontsource-variable/caveat` 5.3.0,
  latin + latin-ext subsets (~104 KB), `@font-face` at the top of `bulletin.css`. This
  npm package fits the `upgrade_vendored_assets` manifest.
- Add the `pin` and `pen` glyphs to `annuaire/templatetags/icons.py`. The prototype
  defines them in `bulletin_tags.py`.
- Pictures and page previews should open in the site's existing image viewer
  (`publication_attachments.js`: zoom, fullscreen, carousel) rather than a new browser
  tab.
- Bugs hit while prototyping. Each is worth a source-text regression test (CLAUDE.md §4):
  - the prose track must be a definite size (`min(100%, 42rem)`), not
    `minmax(0, 42rem)`. Grid sizing shares leftover space evenly between growable
    tracks, and a `minmax()` prose track got a third of a phone's width (the page grew
    2.5× taller);
  - floats only wrap text in the same flow: an article body split into grid items (the
    earlier subgrid layout) cannot dock pictures, hence `display: flow-root`;
  - a hash link into a horizontal scroller only scrolls the target "into view" (page 6
    ended up at the right edge), so `bulletin.js` brings it to the front;
  - an `<img>` with a percentage width inside a shrink-to-fit (`inline-block`) link
    collapses to 0 px, so the link must stay `inline`;
  - on multi-line table-of-contents entries, dot leaders need
    `align-items: last baseline`;
  - scanned paper is grey, so crops blended with `multiply` show a box unless near-white
    is pushed to white (done in `build_package.py`);
  - lazy images stay blank in full-page screenshots, so tests or QA tools must force
    them to load.

## 4. Import feature in `publications`: requirements gathered so far

**Recommended model**: a new `Bulletin` model rather than stretching `BlogPost`, whose
body is Markdown. The validated JSON stays the source of truth and is rendered at
request time, so a design change never requires re-transcribing anything.

- `Bulletin`: `document_id` (unique, e.g. `bc-017`), `series_code`, `series_title`,
  `issue_number` (nullable), `issue_label`, `date_value` (ISO partial date) and
  `sort_date` (DateField, first day of the period, for ordering), `title`, `summary`,
  `data` (JSONField, the whole `bulletin.json`), `schema_version`,
  `source_sha256` + `source_file_name`, `status` (draft/published),
  `imported_by`/`imported_at`/`updated_at`, `search_text` + `search_vector` (full-text
  search over the transcription, like `BlogPost`), and soft delete via
  `SoftDeleteModelMixin`, like `BlogPost`.
- `BulletinImage`: FK to `Bulletin`, `image_id` (unique per bulletin), `file`
  (`ImageField`, `upload_to="bulletins/<document_id>/"`), `kind`, `width`, `height`,
  `sha256`. File cleanup via `register_file_cleanup` (CLAUDE.md §5.4). The renderer maps
  JSON image ids to `BulletinImage.file.url`.
- Optionally attach the original PDF (open question).

**Upload flow** (staff only, staged like the GEDCOM import): upload a `.zip` package,
then the server validates it and shows a **preview page plus a validation report**
(stats, warnings, uncertain and illegible counts, transcription notes). A "Publier"
button then saves atomically.

- Zip safety: reject absolute paths, `..` and symlinks; allow only `bulletin.json` and
  `images/*.{jpg,png,webp}`; cap total size (e.g. 50 MB) and file count; open every image
  with Pillow, which enforces `MAX_IMAGE_PIXELS`; check sha256 and dimensions against the
  JSON.
- Validation = the same two layers as `prototype/validate.py` (to become e.g.
  `publications/bulletin_package.py`, unit-tested with a valid fixture plus broken
  variants, like the 9 used here). Test fixtures must be synthetic, never a real issue:
  `prototype/fixtures/demo-001/` is one. The validator also reports caption coverage
  (pictures, printed captions, added captions) for the review screen.
- **Re-import of the same `id`** updates in place: new JSON, images added, replaced
  (sha256 changed) or deleted. Warn when `source_sha256` differs (a different scan of the
  same issue?). *Open question:* keep previous JSON versions for correction history?

**Pages**: a list of bulletins (by `sort_date`, possibly grouped by decade/year), the
detail page, anchors per article (usable from search results and comments), a
"Bulletins familiaux" nav entry under Publications. Nice-to-haves: comments like
`BlogPost`, a "Quoi de neuf" entry and email notification on publish.

**Visibility**: the site is login-only, so bulletins are visible to all members by
default. *Open question:* group restriction (like documents and albums)? Special policy
for `address` blocks and phone numbers?

## 5. The PDF → package agent: procedure that worked on BC 17

1. **Inspect**: page count, `/Rotate`, text layer (none here; if one exists, use it only
   as a hint and verify visually), metadata (scanner, scan date). Derive `id`, series
   and issue from the file name and the masthead.
2. **Overview**: all pages at low resolution. Identify rubrics, articles, continuations
   across columns and pages, inserts and annexes, graphics, marginalia.
3. **Zoomed transcription**: every page at 200 dpi in strips (4–5 horizontal strips; one
   crop per column on multi-column pages; row bands for tables). BC 17 needed about 40
   crops for 9 pages. Tables: align cells by **vertical position**, allowing for page
   skew (the Marraine column sat about 17 px higher than Code). Empty cells are `null`.
4. **Structure** into the schema, applying the conventions in §2.3.
5. **Doubts**: re-zoom at 400 dpi with contrast; if still unsure, an `uncertain` span
   plus a note; if unreadable, an image.
6. **Draft JSON → `build_package.py` → `validate.py`**, looping until VALID.
7. **Visual QA** (recommended): render the preview and compare it with the page
   previews, e.g. with screenshots.
8. Everything imports as **draft**; a family member reviews before publishing.

Throughput and cost are not measured yet. This first issue was done interactively in one
session. For dozens of PDFs: one agent run per PDF (parallelizable), same toolbox (this
folder's `prototype/` scripts), packaged as a Claude Code skill or as a batch job on the
Claude API. *Open question.*

## 6. Open questions for the spec

1. New `Bulletin` model (recommended) or an extension of `BlogPost`?
2. Should the original PDF be stored on the site (download "le PDF original")?
3. Visibility: all members or group-restricted? Policy for addresses and phone numbers
   (show, hide behind a click, hide)?
4. Transcription conventions `faithful-v1` (spelling kept, accents restored,
   typographic quotes): OK? Or a strictly diplomatic transcription?
5. Handwriting font for handwritten titles, names and signatures: keep it?
6. Corrections after review: re-run the agent with feedback, edit the JSON on the site,
   or per-block corrections?
7. Later links: `news_item.subject` and table names → `annuaire.Person`; the godparent
   table → `genealogy`; `event` blocks → calendar ("il y a 30 ans")? Out of scope for v1?
8. The generated `summary` is the only non-verbatim prose. Keep it, and label it as
   generated?
9. Other series besides BC (the schema already supports a series code)?
10. Annex rule (an announced annex joins its article): OK, or keep strict physical order?
11. Agent execution: interactive skill (human in the loop) vs API batch job?

## 7. Trial log (BC 17)

- Result: 8 articles, 14 images (9 page previews, masthead, photo, flyer, signature,
  pencil note), 58 paragraphs, 7 news items, 2 events, 1 table (48 rows). 2 uncertain
  readings (a nickname on p.3, the byline on p.4), 2 unreadable items kept as images
  (a signature, a pencil note). Package: 2.4 MB. VALID.
- The schema covered everything in the issue without an escape hatch; `gallery` and
  `aside` are still untested.
- Rendering checked in headless Chromium, opened from disk (`file://`) exactly as the
  review export is used: 390, 1366 and 1920 px, Alpenglow and Nightfall. No horizontal
  overflow, no broken image, Bitter, Karla and Caveat all loaded.
- Full-width pass (after the first review): content area uncapped, breakout grid,
  two-column masthead and sommaire.
- Docking pass (after the second review, schema 0.2): single pictures dock right with
  the text wrapping around them, picture groups and the page scans became carousels,
  every picture got a caption line. BC 17's two pictures have no printed caption, so
  they got captions added during transcription. The synthetic `demo-001` issue covers
  what BC 17 lacks (printed captions, a gallery, consecutive figures, an illegible
  word, an aside): VALID, 6 pictures, 6 captions.
- Environment gap: the `run-famille-busson` driver hardcodes Playwright's bundled
  browser, which isn't downloaded in this container. `prototype/shoot.cjs` reuses the
  skill's Playwright install with the system `/usr/bin/chromium`. The driver could accept
  an `executablePath` from an environment variable.

## 8. Reproduce / iterate

From the repo root. The PDF and the agent's draft stay in git-ignored places: the PDF
wherever it was dropped, the draft in `.claude/tmp/bulletins/work/`.

```bash
P=design/bulletins/prototype
T=.claude/tmp/bulletins   # data folder, git-ignored
uv run --no-sync python $P/build_package.py "BC 017 Al 04-1995.pdf" $T/work/bc-017.draft.json $T/packages
uv run --no-sync python $P/make_demo.py   # regenerates the synthetic fixture (byte-identical)
uv run --no-sync --with jsonschema python $P/validate.py $T/packages/bc-017
uv run --no-sync --with jsonschema python $P/validate.py $P/fixtures/demo-001
uv run --no-sync python $P/export.py      # renders both + README + SPEC.md, then zips into $T/export/
E=$PWD/$T/export/famille-busson-bulletins-preview
node $P/shoot.cjs '[{"url":"file://'$E'/bc-017.html","path":".shots/bulletin/x.png","width":1920,"height":1080}]'
```

The export folder opens straight from disk (`file://`, offline). Every page sits at its
root and only references files below it. The zip next to it is the same folder, for
copying to another machine. `prototype/` passes `ruff` (check and format) and adds no `ty`
diagnostic.
