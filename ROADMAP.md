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
