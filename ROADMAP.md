# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `release-workflow` skill) — this file only ever tracks pending
> work.

## Security

- [x] A · Replace plaintext password in the account creation/reset email —
  `BulkAccountCreateView._send_account_credentials_email` sends the temporary password
  in plaintext by email. Acceptable for a first version — it fixes an urgent need (no
  email was being sent at all) — but a plaintext password in an email is never ideal
  (compromised mailbox, unencrypted transit depending on the provider, etc.). Replace
  with a single-use, time-limited password reset link (a signed token, e.g.
  `django.contrib.auth.tokens.PasswordResetTokenGenerator` or equivalent), modeled on
  Django's standard `django.contrib.auth` flow, instead of the password itself.
  (priority: medium)
- [x] B · Require authentication for the home page — the `home` view
  (`annuaire/views.py`) has no `@login_required`, so it's visible to unauthenticated
  users; restrict it like the rest of the app. (priority: high) [#34]
- [x] C · Self-service "mot de passe oublié" flow — once A ships the
  password-reset-confirm view/template, add Django's `PasswordResetView`/
  `PasswordResetDoneView` (project templates, reusing the `password_reset_confirm`
  URL name) so a user who forgets their password can request a new link themselves
  instead of relying on staff re-running the bulk account tool. (priority: medium)
- [x] D · Restrict access to uploaded media files — `/media/<path>` is served with no
  authentication check (`famille_busson/urls.py`), so `Person.profile_photo`,
  `Chalet.photo`, and blog `Attachment` files stay readable by anyone with the URL,
  even after B removes anonymous access to the rest of the app. Add an authenticated
  serve view (or an X-Sendfile/X-Accel handoff) gating access the same way every
  other view is gated. (priority: high)
- [x] E · Adopt `LoginRequiredMiddleware` as defense-in-depth — Django's built-in
  middleware (5.1+) that requires an explicit `@login_not_required` opt-out on every
  public view, so a future new view can't silently repeat the bug fixed in B.
  Requires opting out `CustomLoginView`, `SignupView`, `healthz`, the root redirect,
  and (once D ships) the media serve view. (priority: medium)

---

## Frontend / UX

- [x] A · Responsive design for mobile navigation — replace the always-visible custom
  `.sidebar` in `annuaire/templates/annuaire/base.html` with a Bootstrap 5 offcanvas
  pattern: vendor `bootstrap.bundle.min.js`, add a hamburger toggle below the `lg`
  breakpoint, add media queries to `main.css` so desktop layout is unchanged above it.
  Scoped to the single shared base template — applies to every view. Draft plan already
  posted on the issue. (priority: medium) [#31]
- [x] B · Site favicon — minimalistic SVG mountain-and-trees favicon; already built and
  wired into `base.html` (`<link rel="icon">`) on unmerged branch
  `claude/issue-33-20260816-0830` — open a PR from it rather than redoing the work.
  (priority: low) [#33]

---

## Annuaire — profile improvements

- [ ] A · Address picker for a person's address — autocomplete field in the profile
  create/update views: user types, an address API returns candidates, selecting one
  saves a standard one-liner address format. Proposed API: France's free BAN
  (api-adresse.data.gouv.fr, no key required) — flag if non-French addresses need to be
  supported. (priority: medium) [#32]

---

## Publications — future improvements

Items deferred when the `publications` app was created:

- [ ] A · Multi-author picker — generalize `person_picker.js`
  (`annuaire/static/js/`, currently `document.querySelector` — one instance per page)
  into `querySelectorAll`-based support for multiple instances, and extract the
  duplicated picker markup (currently copy-pasted across 4 templates, including
  `BlogPostForm.authors`) into a shared template include. (priority: low)
- [ ] B · Orphaned file cleanup — Django doesn't delete files under `MEDIA_ROOT` when a
  row referencing them is deleted. The same issue already exists for
  `Person.profile_photo` and `Chalet.photo`; worth handling for all three models at
  once. (priority: low)
