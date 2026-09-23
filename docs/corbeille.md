# Corbeille

When a user deletes a blog post, a document, an album or a photo, it is not destroyed
at once. It goes to the trash ("corbeille"):

- it disappears from all normal pages;
- staff can restore it for 30 days (`TRASH_RETENTION_DAYS`, set in the environment);
- after that, a daily job deletes it for good.

Staff see all items in the trash on the "Corbeille" page, with two buttons for each
item: "Restaurer" and "Supprimer définitivement".

## Scope

Only these four types use the trash: blog posts, documents, albums and photos.
Everything else (relations, comments, events, houses, stays, genealogy data) is still
deleted at once.

People do not use the trash either. To erase a person, staff use anonymisation (see
[`privacy.md`](privacy.md#retention-and-erasure-policy)).

## How it works: `soft_delete()`, never an overridden `Model.delete()`

The four models use `SoftDeleteModelMixin` (in `annuaire/soft_delete.py`). It adds:

- `deleted_at` and `deleted_by`: when and by whom the item was put in the trash;
- `objects`: the normal manager. It **hides** items in the trash. So every existing
  page, and the Django admin, only sees live items, with no extra code;
- `all_objects`: a manager that also returns items in the trash. The trash page and the
  purge job use it;
- three methods: `soft_delete(actor)`, `restore()` and `purge()`.

**Important:** `delete()` is not changed. It still means "delete for good", everywhere
in the code. The code that removes files from disk after a delete still works as
before. To move an item to the trash, call `soft_delete()` instead:

- **`soft_delete(actor)`** — moves the item to the trash and writes a `DELETE` entry in
  the [audit log](audit.md). The four delete pages call it.
- **`restore()`** — takes the item out of the trash and writes a `RESTORE` entry.
- **`purge()`** — writes a `PURGE` entry, then really deletes the item (and its files).

### No cascade: trashing an album doesn't trash its photos

When an album goes to the trash, its photos stay where they are. But photos are only
reachable through their album, so they cannot be seen until the album is restored. The
delete page says this: the photos become unreachable, not deleted.

### Confirm-delete copy

The delete confirmation pages say "récupérable pendant 30 jours" and "Envoyer à la
corbeille". The number of days comes from `TRASH_RETENTION_DAYS`.

## Viewing and managing the corbeille

The trash page (`corbeille/`) is for staff only. It lists all items in the trash, most
recently deleted first. It is linked from "Corbeille" in the Administration section of
the menu, after "Journal d'audit".

The "Restaurer" and "Supprimer définitivement" buttons send a POST request (staff only).
The URL contains the item's type. The site only accepts the four types listed above,
and returns 404 for any other.

## Automatic purge

A job runs every day at **05:00 UTC** (see
[`background_tasks.md`](background_tasks.md#current-scheduled-jobs)). It deletes for
good every item that has been in the trash longer than `TRASH_RETENTION_DAYS`. It
handles items one by one, so an error on one item does not cancel the others.

`TRASH_RETENTION_DAYS` (default `30`) is the only setting for this delay. The job and
the pages all use it.

## Interaction with person erasure

When staff anonymise a person (see
[`privacy.md`](privacy.md#retention-and-erasure-policy)), that person's items in the
trash are deleted for good at once. Otherwise, the data of an "erased" person could
still be restored for up to 30 days.
