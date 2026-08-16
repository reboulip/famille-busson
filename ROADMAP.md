# Roadmap — Famille Busson

> Shipped items are moved to [`docs/ROADMAP_ARCHIVE.md`](docs/ROADMAP_ARCHIVE.md) at
> release time (see the `release-workflow` skill) — this file only ever tracks pending
> work.

## Publications — future improvements (low priority)

Items deferred when the `publications` app was created:

- **Multi-author picker** — `BlogPostForm.authors` uses a plain `SelectMultiple`,
  which is impractical with many people. `person_picker.js` only supports one instance
  per page; generalizing it would let it be reused here.
- **Orphaned file cleanup** — Django doesn't delete files under `MEDIA_ROOT` when a row
  referencing them is deleted. The same issue already exists for `Person.profile_photo`
  and `Chalet.photo`; worth handling for all three models at once.

---

## Security (medium priority)

### Plaintext password in the account creation/reset email
`BulkAccountCreateView` sends the temporary password in plaintext by email (see
`_send_account_credentials_email` in `views.py`). Acceptable for a first version — it
fixes an urgent need (no email was being sent at all) — but a plaintext password in an
email is never ideal (compromised mailbox, unencrypted transit depending on the
provider, etc.).

Eventually, replace it with a single-use, time-limited password reset link (a signed
token, e.g. `django.contrib.auth.tokens.PasswordResetTokenGenerator` or equivalent),
modeled on Django's standard `django.contrib.auth` flow, instead of the password
itself.
