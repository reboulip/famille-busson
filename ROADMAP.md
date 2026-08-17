# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `release-workflow` skill) — this file only ever tracks pending
> work.

## Security

- [ ] A · Replace plaintext password in the account creation/reset email —
  `BulkAccountCreateView._send_account_credentials_email` sends the temporary password
  in plaintext by email. Acceptable for a first version — it fixes an urgent need (no
  email was being sent at all) — but a plaintext password in an email is never ideal
  (compromised mailbox, unencrypted transit depending on the provider, etc.). Replace
  with a single-use, time-limited password reset link (a signed token, e.g.
  `django.contrib.auth.tokens.PasswordResetTokenGenerator` or equivalent), modeled on
  Django's standard `django.contrib.auth` flow, instead of the password itself.
  (priority: medium)
- [ ] B · Require authentication for the home page — the `home` view
  (`annuaire/views.py`) has no `@login_required`, so it's visible to unauthenticated
  users; restrict it like the rest of the app. (priority: high) [#34]

---

## Frontend / UX

- [ ] A · Responsive design for mobile navigation — replace the always-visible custom
  `.sidebar` in `annuaire/templates/annuaire/base.html` with a Bootstrap 5 offcanvas
  pattern: vendor `bootstrap.bundle.min.js`, add a hamburger toggle below the `lg`
  breakpoint, add media queries to `main.css` so desktop layout is unchanged above it.
  Scoped to the single shared base template — applies to every view. Draft plan already
  posted on the issue. (priority: medium) [#31]
- [ ] B · Site favicon — minimalistic SVG mountain-and-trees favicon; already built and
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

- [ ] A · Multi-author picker — `BlogPostForm.authors` uses a plain `SelectMultiple`,
  which is impractical with many people. `person_picker.js` only supports one instance
  per page; generalizing it would let it be reused here. (priority: low)
- [ ] B · Orphaned file cleanup — Django doesn't delete files under `MEDIA_ROOT` when a
  row referencing them is deleted. The same issue already exists for
  `Person.profile_photo` and `Chalet.photo`; worth handling for all three models at
  once. (priority: low)
