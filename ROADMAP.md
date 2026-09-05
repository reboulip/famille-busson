# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `/release` skill's release-time housekeeping step) — this file
> only ever tracks pending work.

## Phase 5

### Cluster: Emails — identité visuelle

- [x] 5.1 · Shared email design system — spec pass — detailed visual specs + static
  mockups for one common branded HTML email base (header/logo/colors/footer,
  unsubscribe-link placement), covering all 5 existing app email touchpoints: the
  birthday-reminder and new-blog-post notifications (`annuaire/email_utils.py`'s
  `send_bulk_emails`, currently inline plain-text f-strings in
  `publications/signals.py` / `send_birthday_reminders.py`), the bulk-account-
  creation/resend email (`annuaire/views.py`'s `_account_setup_email_content`, same),
  and the two `PasswordResetView`-based flows (password reset, magic link — already
  template-file-based but text-only). No existing brand system beyond the
  mountain/trees favicon (`annuaire/static/favicon.svg`) — starts mostly from scratch.
  Must be email-safe HTML (inline CSS, table-based layout for Outlook) with a
  plain-text fallback for every message, not modern CSS. Store specs/mockups in a
  throwaway folder outside `docs/` and outside any app's `templates/` dir (e.g.
  `design/emails/`) — not wired into Django's template loader, for review before 5.2
  builds anything.
- [x] 5.2 · Shared email design system — build — implement the reviewed spec as real
  template(s) and wire all 5 flows onto it. Trigger/filter/subscriber logic for the
  birthday and new-post notifications is unchanged — opt-in checkboxes, deceased-
  profile exclusion, and the connection-cycling bulk sender all already shipped
  correctly (#39, Phase 3 wave 2) — this is a content/rendering swap only. The 3
  raw-`send_mail` flows need to move to multipart sending (`EmailMultiAlternatives` or
  `send_mail(html_message=...)`); the 2 `PasswordResetView`-based flows just need
  `html_email_template_name` set to the new template. (requires: 5.1)

> 5.2 as built, and the decisions taken during it:
> - **The birthday photo is embedded, not linked.** `MEDIA_URL` is served behind
>   `@login_required` on purpose, so an `<img src>` in an email would follow the
>   redirect and render the login page. The photo now travels inside the message as a
>   `multipart/related` part (`annuaire/email_utils.py`), falling back to the initials
>   disc when the person has no photo, the file is unreadable, or it exceeds 400 KB.
> - **The new-post excerpt shipped** (~160 chars via the existing `markdown_plain`),
>   the one place this pass changed content rather than presentation.
> - **CTA buttons are filled `ember` (#9C4A22), not `alpenglow`.** Card-tinted text on
>   alpenglow is 2.98:1 and fails AA for the button label; on ember it is 5.90:1. The
>   site made the same swap, so the two now agree.
> - **`manage.py preview_emails`** renders any of the five flows to HTML (or sends it
>   to a real address) so they can be checked without waiting for a real trigger.

## Phase 6

### Cluster: Site — identité visuelle

- [x] 6.1 · Web design system — design pass — extend the Alpenglow/Nightfall palettes
  from 5.1 to the site itself. Spec, adoptable token/component CSS and six archetype
  mockups in `design/web/` (same throwaway-folder convention as `design/emails/`).
- [x] 6.2 · Web design system — build — implement the reviewed spec across all ~55
  templates: token layer + Bootstrap 5.3 bridge, self-hosted Bitter/Karla, the eaves
  rule on every view, the ten view archetypes, a `base_threshold.html` split for
  logged-out pages, an inline SVG icon set replacing emoji, the shared empty state, and
  Nightfall with a no-flash theme toggle. Reference doc: `docs/design_system.md`.
  (requires: 6.1)

> Deferred out of 6.2, for a later pass:
> - The hub's live one-line summary ("22 profils, 5 chalets, 3 personnes à
>   Praz-sur-Verre cette semaine") — the only place the design pass invented *content*
>   rather than presentation. Needs view work; shipped as a plain date line instead.
> - Retinting family-chart's own node label plates. They are drawn from vendor CSS
>   custom properties that are load-bearing for the card labels, so they still read as
>   grey Bootstrap-era plates against the warm palette.

## Backlog

> Unscoped items held for a future triage pass — not tied to any phase or sprint.
> Promote an item into a numbered `## Phase N` (with a proper `N.M` id) once it's ready
> to be scoped and sprinted.

### Cluster: Profil — adresse secondaire
- [ ] B.1 · Secondary address on profile — let a member add a secondary address to
  their profile, shown on the Carte view, usable to create/locate their chalet.
  Interacts with the Phase 1 chalets self-service work; scope to be refined.
  (priority: tbd) [#53]

### Cluster: Groupes et permissions
- [ ] B.2 · SCI grand chalet group — new group for grand chalet works/news content,
  with author vs. reader roles (SCI project-group members are authors, SCI
  shareholders are readers). Needs a groups/roles/permissions design pass first — no
  such model exists yet. (priority: tbd) [#57]

### Cluster: Sécurité
- [ ] B.3 · Throttle unauthenticated email-sending endpoints — rate-limit the
  password-reset and magic-link request views; needs a shared cache backend first
  (current `CACHES` setting is unset, defaulting to per-worker `LocMemCache`, which a
  throttle built on it would trivially bypass). (priority: tbd)
