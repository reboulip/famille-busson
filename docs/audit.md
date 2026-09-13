# Journal d'audit

Phase 14's second privacy-adjacent feature: a staff-visible log of who created,
changed, deleted, or restored the site's more sensitive records, and who was
added to or removed from a group or from a person's `owners`. Signal-driven and
opt-in — a model is tracked only if its app's `signals.py` explicitly registers
it, never by walking every model in the project.

## What's tracked

| Model / relation | Registered from | Fields diffed on update |
|---|---|---|
| `annuaire.Person` | `annuaire/signals.py` | `first_name`, `last_name`, `email`, `phone_number`, `postal_address`, `latitude`, `longitude`, `birth_date`, `birth_place`, `deceased`, `death_date`, `death_place`, `description`, `export_privacy` |
| `annuaire.Relation` | `annuaire/signals.py` | `person1_id`, `person2_id`, `relationship_type`, `start_date`, `marriage_place`, `end_date` |
| `documents.Document` | `documents/signals.py` | `title`, `category_id`, `document_date`, `description`, `uploaded_by_id`, `redactor_id` |
| `photos.Album` | `photos/signals.py` | `title`, `description`, `date_start`, `date_end`, `cover_id`, `created_by_id` |
| `photos.Photo` | `photos/signals.py` | `caption`, `taken_at`, `uploaded_by_id`, `album_id` |
| `Account.groups` membership (both edit directions) | `annuaire/signals.py` | — (membership add/remove, not a field diff) |
| `Person.owners` membership (both edit directions) | `annuaire/signals.py` | — (membership add/remove, not a field diff) |

For the five plain models, **create** and **delete** are always logged;
**update** is only logged if one of the listed fields actually changed value —
saving a model with no change to any tracked field writes nothing.

For the two M2Ms, Django fires `m2m_changed` differently depending on which
side of the relation the edit came from — e.g. `GroupMembersUpdateView` edits
via the *reverse* accessor (`group.account_set.set(...)`), not the forward
`account.groups`. `register_m2m_membership_audit()`
(`annuaire/audit.py`) handles both directions and always attributes the event
to the affected `Account` (for group membership) or managed `Person` (for
owners) — never to the `Group` itself, since "who gained/lost access" is what
an audit trail needs, not the group's own row.

## What's deliberately excluded

`register_audit(model, *, fields)` diffs an explicit **allowlist** of field
names, never every field on the model by reflection. This is a structural
guarantee, not a filter applied after the fact: a field that isn't named in the
`fields=[...]` list passed at registration can never appear in an `AuditEvent`.
In particular, `Account.password`, `Account.calendar_token`, and the
`search_vector`/`search_text` full-text-search columns are never passed to any
`register_audit()` call, so they can't leak into the log even if a future edit
to `annuaire/signals.py` widens another model's allowlist.

**Not yet audited at all:** `Comment`, `Event`, `Chalet`, `PresencePSV`, and
every `genealogy` model (`Story`, `Source`, `Citation`, `GedcomImport`, etc.).
`Relation`'s own row is tracked, but not the side-effects of deleting it
(the automatic inverse-`Relation` deletion described in `CLAUDE.md` §5 doesn't
itself produce a separate audit row beyond the two `Relation` rows). This is a
known gap for this wave, not a design decision to leave these untracked
forever.

## How the actor is captured

`AuditActorMiddleware` (`annuaire/middleware.py`) reads `request.user` once per
request and stores it in a `contextvars.ContextVar`, the same idiom the
existing `RequestIdMiddleware` uses for request correlation IDs. It's
registered in `MIDDLEWARE` (`config/settings.py`) right after
`AuthenticationMiddleware`, so `request.user` is already resolved by the time
it runs. `annuaire.audit`'s signal receivers — which run deep inside
`.save()`/`.delete()`, with no access to the request object — read the
contextvar via `get_current_actor()` to attribute the resulting `AuditEvent` to
whoever made the change.

For a write with no request in flight — a management command, a background
job, a data migration — the contextvar is unset, so `actor` is recorded as
`None`. `AuditEvent.actor_label` still gets set from `str(actor)` at write
time whenever an actor *was* captured, and survives independently of the
`actor` foreign key (`on_delete=models.SET_NULL`) — so a row still shows who
acted even after that `Account` is later deleted or anonymised.

## Row survival: content type + object id, not a GenericForeignKey

`AuditEvent` stores `content_type` (FK to `ContentType`), `object_id` (plain
`CharField`, not a FK) and `object_repr` (a `str(instance)` snapshot taken at
write time) — deliberately not a `GenericForeignKey` resolving live to the
tracked row. This means a row about an object that has since been deleted (or,
from 14.5 onward, purged from the corbeille) still renders correctly in the
log: `object_repr` shows what the object *was*, rather than the log entry
breaking or silently disappearing once the underlying row is gone.

## Viewing the log

`AuditLogListView` (`annuaire/views.py`, route name `audit-log-list`,
`personne`/`documents`/`photos` events all in one place) lists every
`AuditEvent`, most recent first, paginated 20 per page. Staff-only (see
[`permissions.md`](permissions.md)). Linked from "Journal d'audit" in the
staff-only Administration block of the main nav
(`annuaire/templates/annuaire/base.html`), and rendered by
`annuaire/templates/annuaire/audit_event_list.html` as a table of timestamp,
actor, action, object, and changes.

## Corbeille (soft-delete / restore / purge)

The corbeille (14.5) needed no new `AuditEvent.Action` values — the three
already declared on the model cover it exactly: trashing a `BlogPost`/
`Document`/`Album`/`Photo` logs `DELETE` (same action a hard delete would have
logged), restoring it logs `RESTORE`, and a permanent purge (by staff, or by
the daily `purge_expired_trash` job once an item is past
`TRASH_RETENTION_DAYS`) logs `PURGE`. All three come from
`SoftDeleteModelMixin`'s `soft_delete()`/`restore()`/`purge()` methods
(`annuaire/soft_delete.py`), not from `register_audit()`'s normal
create/update/delete signal wiring — see [`corbeille.md`](corbeille.md) for the
full feature.

One fix landed alongside this wave: `record_audit_event()` now accepts an
explicit `actor` keyword, instead of always reading the ambient request-scoped
contextvar (`get_current_actor()`). `soft_delete(actor)` — whose caller already
has the acting `Account` in hand, passed in directly by the delete view
(`self.object.soft_delete(request.user)`) — passes that same argument straight
through to `record_audit_event()`. Before the fix, an explicit `actor` argument
like this one was silently discarded in favour of reading the contextvar
instead; it only coincidentally matched in the normal view-triggered case,
since the contextvar holds `request.user` there too. `restore()` and `purge()`
take no actor of their own and still resolve purely from the contextvar — via
`CorbeilleRestoreView`/`CorbeillePurgeView` for a staff action (attributed to
the staff member), or `None` when `purge()` runs from the `purge_expired_trash`
background job, where no request/contextvar exists at all.

## Anonymisation (14.2)

Erasing/anonymising a `Person` (see [`privacy.md`](privacy.md#retention-and-erasure-policy))
logs one `AuditEvent` with the `ANONYMISE` action — a dedicated `AuditEvent.Action`
value added specifically for this operation, since it's neither a plain field
update nor a corbeille action: it blanks a `Person`'s identity in place, rather
than changing a handful of tracked fields or moving a row in or out of the
trash. `anonymise_person()` (`annuaire/anonymisation.py`) calls
`record_audit_event()` directly with an explicit `actor` (the staff member who
triggered it), the same explicit-`actor` pattern `soft_delete()` uses above,
rather than going through `register_audit()`'s normal per-field diff.

`Person` is itself registered with `register_audit()` (see "What's tracked"
above), and most of the fields anonymisation blanks are in that model's
diffed allowlist — so without precaution, saving the blanked `Person` would
also fire the normal field-level `UPDATE` event alongside the explicit
`ANONYMISE` one, and that `UPDATE` row's `changes` JSON would permanently
store the person's *pre-anonymisation* values (old name, email, etc.) as the
`"from"` side of the diff, defeating the very erasure the operation is meant
to guarantee. `anonymise_person()` avoids this with `suppress_generic_audit()`
(`annuaire/audit.py`): a context manager, backed by its own request-scoped
contextvar, that makes `register_audit()`'s three receivers (`_on_pre_save`,
`_on_post_save`, `_on_post_delete`) no-op for its duration. `anonymise_person()`
wraps just the `person.save()` call in `with suppress_generic_audit():` — so
anonymising a person now produces exactly **one** `AuditEvent` for the `Person`
row, the explicit `ANONYMISE` action with no old-value payload, not two.

`suppress_generic_audit()` is a general-purpose escape hatch, not
`Person`/anonymisation-specific: it's the right tool for any future operation
that already emits its own more specific audit event and where
`register_audit()`'s generic per-field diff would otherwise leak retired or
otherwise-sensitive data. `anonymise_person()` is its only caller today.
