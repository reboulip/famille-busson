# Journal d'audit

The audit log records who created, changed, deleted or restored sensitive records. It
also records who was added to or removed from a group, or from a profile's owners. Only
staff can see it.

A model is recorded only if it is registered explicitly in its app's `signals.py`.

## What's tracked

| Model / relation | Registered in | Fields recorded on change |
|---|---|---|
| `annuaire.Person` | `annuaire/signals.py` | `first_name`, `last_name`, `email`, `phone_number`, `postal_address`, `latitude`, `longitude`, `birth_date`, `birth_place`, `deceased`, `death_date`, `death_place`, `description`, `export_privacy` |
| `annuaire.Relation` | `annuaire/signals.py` | `person1_id`, `person2_id`, `relationship_type`, `start_date`, `marriage_place`, `end_date` |
| `annuaire.SiteConfig` | `annuaire/signals.py` | The site settings, except the logo and icon (see [`site_config.md`](site_config.md)). |
| `documents.Document` | `documents/signals.py` | `title`, `category_id`, `document_date`, `description`, `uploaded_by_id`, `redactor_id` |
| `photos.Album` | `photos/signals.py` | `title`, `description`, `date_start`, `date_end`, `cover_id`, `created_by_id` |
| `photos.Photo` | `photos/signals.py` | `caption`, `taken_at`, `uploaded_by_id`, `album_id` |
| Group membership | `annuaire/signals.py` | — (who was added or removed) |
| Profile owners | `annuaire/signals.py` | — (who was added or removed) |

For models, **creation** and **deletion** are always recorded. A **change** is
recorded only if one of the listed fields really changed.

For group membership, each entry is about the account that gained or lost access, not
about the group. This works whichever side the change was made from.

## What's deliberately excluded

Only the fields listed at registration are recorded. A field that is not in the list
can never appear in the log. For example, passwords, calendar links and search data are
never recorded.

**Not recorded yet:** comments, events, houses, stays, and the genealogy models
(stories, sources, citations, GEDCOM imports). This is a known gap, not a final choice.

## How the actor is captured

A middleware saves the logged-in user at the start of each request. The audit code
then uses it to record who made the change.

When there is no request (a management command, a background job, a migration), the
actor is empty. The actor's name is also saved as text. So an entry still shows who
acted, even after that account is deleted or anonymised.

## Row survival: content type + object id, not a GenericForeignKey

Each entry saves the object's type, its id, and its name as text at that moment. It
does not keep a live link to the object. So an entry about a deleted object still shows
correctly: it shows what the object *was*.

## Viewing the log

The log is at the "Journal d'audit" link, in the Administration section of the menu
(staff only). It shows the date, the actor, the action, the object and the changes,
newest first, 20 per page.

## Corbeille (soft-delete / restore / purge)

The trash (see [`corbeille.md`](corbeille.md)) records three actions:

- moving an item to the trash is recorded as `DELETE`;
- restoring it is recorded as `RESTORE`;
- deleting it for good is recorded as `PURGE`.

When the daily job deletes old items from the trash, there is no user, so the actor is
empty.

## Anonymisation (14.2)

Anonymising a person (see [`privacy.md`](privacy.md#retention-and-erasure-policy))
records one entry with the `ANONYMISE` action and the staff member who did it.

Normally, saving a profile records the old and new values of each changed field. For an
anonymisation, this would keep the erased name, email, etc. in the log, and the
erasure would be pointless. To avoid this, anonymisation turns off the normal
recording while it saves the profile, with `suppress_generic_audit()` (in
`annuaire/audit.py`). So there is only one entry, with no old values.

You can use `suppress_generic_audit()` for any future operation that records its own
entry and must not leak old values.
