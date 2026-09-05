# Email design spec — Phase 5.1

Design pass for ROADMAP.md 5.1. **Nothing in this folder is wired into Django** — it's a
throwaway spec for review before 5.2 builds the real templates. Trigger/filter/subscriber
logic for the birthday and new-post emails is unchanged; this only redefines what the
emails look like.

Direction: light, warm, evocative of the Alps — a chalet, not a corporate app. Two named
palettes, not just "light" and "dark": **Alpenglow** (day) and **Nightfall** (night over
the valley). Same structure, different light.

## Why these choices

- **CSS-only motif, no image files.** Most clients block images until the reader clicks
  "download images" — including on first open, which is when a birthday/new-post email
  is most likely to be read. A photo header would be invisible exactly when it matters
  most. The mountain ridge is built from coloured table cells and a bordered-triangle
  technique instead, so it's there from the first render.
- **Two treatments, one identity.** Birthday and new-post notifications get the full
  ridge + wordmark + warm flourishes. Password reset, magic link, and account setup
  share the same card, palette, and type system but drop the ridge to a single low
  horizon line and drop the gold/photo flourishes — a credential email that looks
  understated reads as more trustworthy, and it's a lighter lift for spam filters that
  weigh heavy styling on transactional mail.
- **`Person.profile_photo` is content, not decoration.** The "no images" call above is
  about the *decorative brand chrome* (the ridge). A member's own profile photo on the
  birthday email is real content, same as any product photo in any email — it stays an
  `<img>`, with an initials-circle fallback for when no photo is set or images are
  blocked.

## Palette

### Alpenglow (light)

| Token | Hex | Use |
|---|---|---|
| `parchment` | `#F6EEE0` | Page ground, outside the card |
| `card` | `#FFFAF0` | Card surface |
| `ink` | `#3A2C1E` | Primary text |
| `bark` | `#7A6650` | Secondary/muted text |
| `alpenglow` | `#D9793F` | Primary accent — CTA buttons, links, heading rule |
| `ember` | `#9C4A22` | Deeper accent — button hover/border, tallest peak |
| `spruce` | `#4B5D3F` | Near mountain layer |
| `slate-mist` | `#9FB0AE` | Far mountain layer (atmospheric haze) |
| `snowcap` | `#FBF6EC` | Peak highlight on the tallest ridge |
| `gold` | `#D9A441` | Birthday-only highlight (photo ring) |
| `border` | `#E6D8C3` | Hairline rules, card border |

### Nightfall (dark)

| Token | Hex | Use |
|---|---|---|
| `night` | `#221810` | Page ground |
| `card-dark` | `#2C2119` | Card surface |
| `ivory` | `#F2E6D5` | Primary text |
| `dust` | `#B9A68F` | Secondary/muted text |
| `ember-bright` | `#E2914E` | Primary accent — CTA buttons, links |
| `moon` | `#6B7FA0` | Far mountain layer — moonlit ridge |
| `pine-dark` | `#28331F` | Near mountain layer |
| `starlight` | `#3A3450` | Sky band behind the ridge |
| `gold-dark` | `#E8B85B` | Birthday-only highlight (photo ring) |
| `border-dark` | `#4A3B2E` | Hairline rules, card border |

Contrast checked for body text on its own surface (`ink` on `card`, `ivory` on
`card-dark`) — both clear WCAG AA for normal text. `bark`/`dust` are reserved for footer
microcopy and captions, not body copy.

## Typography

Custom web fonts are not reliable across email clients (Outlook desktop's Word rendering
engine ignores `@font-face` entirely). The design leans on the *character* of an
email-safe fallback stack rather than depending on a webfont loading:

- **Headings** — `Georgia, 'Noto Serif', 'Droid Serif', serif`. Chosen for its weight and
  warmth relative to the other system-serif options — reads closer to a carved wood sign
  than a neutral text face. This is what every recipient sees, not a fallback of last
  resort.
- **Body / UI** — `'Trebuchet MS', Verdana, Helvetica, Arial, sans-serif`. Trebuchet has a
  bit more warmth than Helvetica while staying near-universal; Verdana/Helvetica/Arial
  carry it everywhere else.
- Wordmark and footer legal text: small caps feel via `letter-spacing`, not
  `font-variant`, since the latter is inconsistently supported in email.

The showcase preview (see below) additionally illustrates the aspirational look with
**Bitter** (headings) and **Karla** (body) — real Google Fonts, for clients that *do*
support them. That pairing is illustration only; the shipped email must look complete on
the Georgia/Trebuchet fallback alone, because most recipients will only ever see that.

## The mountain ridge

Three uneven peaks (not a symmetric triangle row — real skylines aren't even), built with
the bordered-`<div>` triangle technique, sitting on a flat sky-band colour. The tallest
peak carries a small second, lighter triangle near its tip as a snowcap. Layering (back
to front): `slate-mist` far ridge → `spruce` near ridge, each peak offset so they
overlap slightly, implying depth. At night the same structure swaps to `moon` (far) /
`pine-dark` (near) against a `starlight` sky band — a moonlit ridge, not an inverted
daytime one.

Below the ridge, a two-rule "eaves line" (a 2px `ink`/`ivory` rule directly under a 1px
`border` rule) marks where the ridge band meets the card content — a nod to the fascia
trim under a chalet roof edge.

**Outlook fallback:** the border-triangle technique is inconsistently rendered by
Outlook's Word engine (peaks can render as small rectangles instead of points). Each
mockup wraps the ridge in `<!--[if !mso]><!-- ... --><![endif]-->` / `<!--[if mso]>`
conditional comments: Outlook gets a flat two-band sky/ridge colour strip with no
triangles, every other client gets the full ridge. Both read as "mountains," neither
breaks.

**Restrained variant** (password reset / magic link / account setup): the ridge band
collapses to a single flat horizon line in `spruce` (`pine-dark` at night) at a fraction
of the height, no peaks, no snowcap. Same eaves line beneath it.

## Layout

Single-column, 600px-max card centred on the parchment/night ground. Ridge band across
the top of the card, wordmark ("Famille Busson") set small and letter-spaced into the sky
band like a signpost. Body content is **left-aligned**, not centred — it reads as a
letter, not a poster. One solid CTA button (`alpenglow`/`ember-bright` fill, `card`-tinted
text, generous padding, modest `border-radius` — Outlook ignores the radius and shows a
square button, which is an acceptable degrade). Footer sits below a plain hairline rule,
small `bark`/`dust` text.

Two footer variants:
- **Notification** (birthday, new post) — includes the settings/unsubscribe link, unchanged
  copy pattern from the current implementation.
- **Transactional** (password reset, magic link, account setup) — no unsubscribe link
  (there's nothing to unsubscribe from); states who sent it and why instead.

## Dark mode

`<meta name="color-scheme" content="light dark">` and
`<meta name="supported-color-schemes" content="light dark">` in `<head>`, plus a `<style>`
block with `@media (prefers-color-scheme: dark)` overrides on classed elements
(`!important`, since inline styles otherwise win). This is real, supported technique in
Apple Mail, iOS Mail, and Outlook.com/new Outlook — not universal (Gmail's app-level
forced-dark heuristics are the main gap), but the explicit `color-scheme` meta is exactly
what tells supporting clients "this message already has an intentional dark mode, don't
auto-invert it," which is the main risk we're guarding against now that Nightfall exists
as a deliberate palette rather than an afterthought.

## Per-email specs

### Birthday reminder — full treatment
- **File:** `birthday-reminder.html`
- Subject (unchanged): `Anniversaire de {Prénom} {Nom}`
- Heading: "C'est l'anniversaire de {Prénom} aujourd'hui !"
- `Person.profile_photo` shown as a circular image (120px) with a `gold`/`gold-dark` ring;
  falls back to a plain initials circle in `alpenglow`/`ember-bright` when no photo is set
  — no image dependency either way for the fallback state.
- Body: one line inviting the reader to wish them well.
- CTA: "Voir le profil de {Prénom}" → profile URL (unchanged link logic).
- Footer: notification variant.

### New blog post — full treatment
- **File:** `new-blog-post.html`
- Subject (unchanged): `Nouvel article : {title}`
- Heading: the post title, in the heading serif.
- Byline: "Par {auteurs}", muted.
- **New content, not in the current plain-text version:** a short excerpt (~160
  characters of the post body, stripped of markdown/HTML). Low-risk addition — reuses the
  existing `markdown_plain` filter already used for document/category card excerpts, so
  5.2 doesn't need new stripping logic. Flagging for explicit approval since it's the one
  place this pass touches *content*, not just presentation.
- CTA: "Lire l'article" → post URL (unchanged link logic).
- Footer: notification variant.

### Password reset / magic link / account setup — restrained treatment
- **File:** `auth-transactional.html` (built as the password-reset copy; magic link and
  account setup are the same shell with only the strings below swapped)
- Single low horizon line, no peaks, no gold, no photo.
- Subject / heading / CTA per flow:

  | Flow | Heading | CTA |
  |---|---|---|
  | Password reset | "Réinitialisez votre mot de passe" | "Choisir un nouveau mot de passe" |
  | Magic link | "Votre lien de connexion" | "Se connecter" |
  | Account setup | "Votre compte Famille Busson" | "Configurer mon compte" |

- Security microcopy under the button (unchanged in substance from current copy): link
  validity window + "if this wasn't you, ignore this email."
- Footer: transactional variant (no unsubscribe link).

## Accessibility

- Body text pairs meet WCAG AA at normal size on their own surface (see palette note
  above).
- No meaningful images requiring alt text in the decorative chrome (it's markup, not
  pictures). The one real image — `profile_photo` — gets `alt="Photo de {Prénom}"`.
- `lang="fr"` on `<html>`, real heading text (not styled-to-look-like-a-heading `<div>`s),
  layout tables marked `role="presentation"` so screen readers skip straight to content.

## Files in this folder

| File | What it is |
|---|---|
| `SPEC.md` | This document |
| `birthday-reminder.html` | Standalone, real email-safe HTML — open directly in a browser |
| `new-blog-post.html` | Standalone, real email-safe HTML |
| `auth-transactional.html` | Standalone, real email-safe HTML (password-reset copy; see table above for the other two flows' strings) |

## Open items for 5.2

- Decide bulletproof-button technique for pixel-perfect Outlook buttons (VML ghost
  button) vs. the padded-`<a>` approach used in these mockups (simpler, already a fine
  degrade — square corners, same padding).
- Wire the new-post excerpt through `markdown_plain` and pick a truncation length.
- Confirm `SITE_BASE_URL`-relative asset hosting for `profile_photo` renders correctly
  in-email (absolute URL, already the pattern used for profile/post links today).
