# Corbeille

Deleting a `BlogPost`, `Document`, `Album`, or `Photo` soft-deletes it instead
of destroying it immediately: the row is marked trashed, hidden from every
normal listing, and stays recoverable for `TRASH_RETENTION_DAYS` days (default
30, env-configurable) before a daily background job purges it for good. A
staff-only "Corbeille" page lists every trashed row across all four models,
with per-row "Restaurer" / "Supprimer définitivement" actions.

## Scope

Publications (`BlogPost`), `documents.Document`, `photos.Album`, and
`photos.Photo` only. **Not** `Person` — removing a person is a separate,
not-yet-built item (14.2's planned anonymisation flow, see
[`privacy.md`](privacy.md)), with different concerns (family-tree integrity,
`person_merge.py`'s meta-guard) than a trashable content row. Nothing else in
the project is soft-deletable; `Relation`, `Comment`, `Event`, `Chalet`,
`PresencePSV`, and the `genealogy` models still hard-delete exactly as before.

## How it works: `soft_delete()`, never an overridden `Model.delete()`

`SoftDeleteModelMixin` (`annuaire/soft_delete.py`), an abstract model mixin
applied to `BlogPost`, `Document`, `Album`, and `Photo` (each also sets
`Meta.default_manager_name = "objects"` explicitly), adds:

- `deleted_at` (nullable timestamp) and `deleted_by` (FK to `Account`,
  `SET_NULL`).
- `objects` — the default manager, filtered to `deleted_at__isnull=True`
  (`SoftDeleteManager`/`SoftDeleteQuerySet`). Every existing view, reverse
  relation, and the admin changelist sees only live rows automatically,
  with no code changes needed at each call site.
- `all_objects` — a plain, unfiltered `Manager`, the escape hatch used by the
  corbeille listing and the purge job to reach trashed rows.
- `soft_delete(actor)`, `restore()`, `purge()` — see below.

The load-bearing design decision is that **this module never overrides
`Model.delete()`** — `.delete()` keeps meaning "really, permanently delete"
everywhere in the codebase: `person_merge.py`'s `loser.delete()`, the
file-cleanup `post_delete` receivers (`annuaire/file_cleanup.py`,
`documents/signals.py`, `photos/signals.py`), and `Relation`'s own
inverse-delete signal (`annuaire/signals.py`) all still fire correctly, and
only at the moment the bytes/rows actually need to go away. Soft-deleting is a
separate, explicit method call instead:

- **`soft_delete(actor)`** — sets `deleted_at`/`deleted_by`, saves, and logs
  an `AuditEvent` `DELETE` action (see [`audit.md`](audit.md)'s "Corbeille" section).
  The four existing delete views (`BlogPostDeleteView`, `DocumentDeleteView`,
  `AlbumDeleteView`, `PhotoDeleteView`) now call `self.object.soft_delete(request.user)`
  from `form_valid()` instead of Django's default `.delete()`.
- **`restore()`** — clears `deleted_at`/`deleted_by`, saves, logs `RESTORE`.
- **`purge()`** — logs `PURGE`, then calls the real `Model.delete()`, firing
  every normal `post_delete` receiver (file cleanup, etc.) exactly as a direct
  hard delete always did.

### No cascade: trashing an album doesn't trash its photos

Soft-deleting an `Album` does **not** soft-delete its `Photo`s. Every photo
read path is already album-scoped (`photos.access.accessible_photos()`), so a
trashed album's photos simply become unreachable through normal
album-scoped browsing until the album is restored (or purged, at which point
the photos' own rows are unaffected — only the album row and its own files go
away). The album delete-confirmation template's copy reflects this: it warns
that the photos become inaccessible while the album is trashed, not that they
get deleted alongside it.

### Confirm-delete copy

The four confirm-delete templates (blog post, document, album, photo) were
reworded from "Cette action est irréversible" / "Supprimer définitivement" to
"récupérable pendant {{ trash_retention_days }} jours" / "Envoyer à la
corbeille" — `trash_retention_days` comes from the new
`annuaire.context_processors.trash_retention` context processor, exposed
site-wide and also used on the corbeille page itself.

## Viewing and managing the corbeille

`CorbeilleListView` (`annuaire/views.py`, route `corbeille/`, name
`corbeille-list`) is staff-only and lists every trashed row across
`CORBEILLE_MODELS` — a hardcoded allowlist of `(app_label, model_name)` pairs
(`publications.blogpost`, `documents.document`, `photos.album`,
`photos.photo`) — most recently deleted first, via each model's `all_objects`
manager. Linked from "Corbeille" in the staff-only Administration block of the
main nav, right after "Journal d'audit".

Each row's "Restaurer" and "Supprimer définitivement" actions are separate,
POST-only, staff-only views: `CorbeilleRestoreView` (`corbeille/<app_label>/<model_name>/<pk>/restaurer/`,
name `corbeille-restore`) and `CorbeillePurgeView` (`.../purger/`, name
`corbeille-purge`). Both resolve the target model via `_get_corbeille_model()`,
which 404s unless `(app_label, model_name)` is in `CORBEILLE_MODELS` — the
model to act on is **never** taken from the URL as an arbitrary lookup, only
validated against that fixed allowlist.

## Automatic purge

`purge_expired_trash()` (`annuaire/tasks.py`) runs daily at **05:00 UTC** (see
[`background_tasks.md`](background_tasks.md#current-scheduled-jobs) —
registered by `annuaire/management/commands/sync_scheduled_tasks.py`, a
distinct hour from the existing 03:00/07:00/08:00 UTC jobs). It finds every
row across `BlogPost`, `Document`, `Album`, `Photo` whose `deleted_at` is older
than `TRASH_RETENTION_DAYS` days ago, and calls `purge()` on each — **one
object per transaction**, deliberately not one `atomic()` block around the
whole batch, so a mid-batch failure never rolls back an already-committed
purge, and each object's deferred `post_delete` file cleanup fires at the
right moment for that object alone.

`TRASH_RETENTION_DAYS` (`config/settings.py`, env-backed, default
`30`) is the single source of truth for the retention window, read by both the
purge job and the confirm-delete/corbeille templates' copy.

## Interaction with person erasure

Anonymising a `Person` (see [`privacy.md`](privacy.md#retention-and-erasure-policy))
purges that person's own trashed `BlogPost`/`Document`/`Album`/`Photo` rows
immediately, ahead of their normal `TRASH_RETENTION_DAYS` window — leaving them
sitting recoverable in the corbeille for up to 30 more days after the person
has supposedly been erased would defeat the erasure guarantee.
