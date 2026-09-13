# Vie privée et traçabilité

Phase 14 groups the site's privacy-facing features: personal data export (14.1),
erasure/anonymisation (14.2), and a privacy notice/consent record (14.3), below.
Two related features live on their own pages rather than here: the staff-only
[audit log](audit.md) (14.4) and the [corbeille](corbeille.md) soft-delete/restore/
purge trash (14.5) — both cross-reference this page where they touch it (audit
logs an anonymisation event; erasure purges a person's trashed rows immediately,
see "Retention and erasure policy" below).

## Personal data export

Any member who can already edit a profile can download a `.zip` archive of
everything the site holds on that `Person`, via the "Télécharger mes données"
button next to "Modifier le profil" on the profile page
(`annuaire/templates/annuaire/personne_detail.html`), or directly at
`personne/<int:pk>/donnees/` (route name `person-data-export`,
`PersonalDataExportView` in `annuaire/views.py`). Access is gated by the same
`can_edit_person()` helper as editing the profile itself — self, staff/superuser,
or an owner of an accountless profile — see
[`permissions.md`](permissions.md)'s "By view" table.

The archive is built synchronously by `annuaire/personal_data.py`'s
`build_personal_data_archive()` and contains:

- `donnees.json` — the structured payload, one key per category below.
- `LISEZ-MOI.txt` — a French readme summarising each category and its item count.
- the profile photo file, under `photo-profil.<ext>`, if the profile has one.

### Scope: metadata and links only, one exception

The export lists **metadata and in-app links**, not the underlying files —
a document row links to `document-detail` rather than embedding the PDF, a photo
row links to `photo-detail` rather than embedding the image, and so on. **The
profile photo is the one deliberate exception**: its bytes are embedded directly
in the archive, since it's the subject's own small, low-risk image rather than a
family document or another member's photo.

### Access model: scoped through the viewer, not the subject

Every category is collected through the **requesting viewer's own access**, using
the same helpers the rest of the app already uses for that content — never a
raw `Model.objects.all()`. Concretely: `documents` via
`documents.access.accessible_documents(viewer)`, `photos` via
`photos.access.accessible_albums(viewer)`/`accessible_photos(viewer)`,
`evenements` via `events.access.accessible_events(viewer)`. This means the
export can never show the person requesting it more than they could already see
elsewhere in the app — for example, staff exporting a member's data still won't
see a document in a category staff can't open, and a profile owner exporting an
accountless dependent's data still won't see a restricted album they're not in
the group for.

### Personal data categories

| Key | Label | Covers |
|---|---|---|
| `profil` | Profil | Profile fields: name, contact details, address/coordinates, birth/death info, description, export-privacy choice, whether a profile photo is set, creation date, link to the profile. |
| `relations_familiales` | Relations familiales | Every family `Relation` involving this person (parent/enfant, conjoint), with type, the other person, and marriage/end dates where set. |
| `comptes_geres` | Comptes gérés | Profiles this person owns (`Person.owners`), and profiles that own this one, if it's accountless. |
| `parametres` | Préférences de notification | The linked `Settings` row's notification toggles (anniversaires, publications, événements). |
| `places` | Résidences | Places this person is listed as an owner of. |
| `presences` | Présences | This person's `Stay` records (unrestricted data — no access helper needed, same posture as the présences calendar elsewhere in the app). |
| `publications` | Publications | Blog posts this person is a listed author of. |
| `commentaires` | Commentaires | Comments this person posted, with a short excerpt and a link to the parent post. |
| `documents` | Documents | Documents this person uploaded or redacted, restricted to what the viewer can see via `accessible_documents(viewer)`. |
| `photos` | Photos | Albums created, photos uploaded, photos this person is tagged in, and tags this person made on others, restricted to what the viewer can see via `accessible_albums(viewer)`/`accessible_photos(viewer)`. |
| `evenements` | Événements | Events created or organised by this person, and this person's RSVPs, restricted to what the viewer can see via `accessible_events(viewer)`. |
| `genealogie` | Généalogie | Life stories about or written by this person, citations against sources, sources added, and GEDCOM import records (uploads, staged-individual matches/creations) involving this person. |
| `consentements` | Consentements | The acceptance of the privacy notice tied to this person's account: the accepted version string and the acceptance timestamp. Empty if the profile has no linked `Account`, or that account hasn't accepted yet. |

Every relation onto `Person` is enumerated explicitly in
`PERSONAL_DATA_RELATIONS`/`PERSONAL_DATA_HIDDEN_RELATIONS`
(`annuaire/personal_data.py`) — a test walks `Person._meta.get_fields()` to make
sure a newly added foreign key or many-to-many onto `Person` can't silently
escape the export uncovered.

## Retention and erasure policy

A staff-only flow (`annuaire/anonymisation.py`'s `anonymise_person(person, actor=...)`,
reachable via the "Anonymiser" button on the profile page — staff only, and hidden
once a person is already anonymised — at `personne/<int:pk>/anonymiser/`, route
name `person-anonymise`, `PersonAnonymiseView`) irreversibly blanks a `Person`'s
identity while deliberately **preserving referential integrity**: unlike
`person_merge.py`'s winner/loser model, nothing is repointed to a different
`Person` row — every authorship/upload relation keeps pointing at the same,
now-anonymised, row. The two modules (`anonymisation.py`/`person_merge.py`)
never call into each other; they solve different problems. Anonymisation is
one-way — `Person.anonymised_at` is set once and never cleared — and refuses to
run twice, or to deactivate the last active staff `Account`.

### What's blanked

On `Person`: `first_name`/`last_name` (replaced with the fixed placeholder
"Personne anonymisée" — deliberately not a real-sounding name), `email`,
`phone_number`, `postal_address`, `latitude`/`longitude`, `birth_date`/`birth_place`,
`death_date`/`death_place`, `description`, and `profile_photo`. `export_privacy`
is set to `REDACT`, reusing `annuaire/privacy.py`'s existing redaction machinery
so every export surface (GEDCOM, Excel, iCal) honours the erasure with zero new
call sites. `person.owners` is cleared.

If the person has a linked `Account`, it's deactivated (`is_active = False`),
its password invalidated (`set_unusable_password()`), its calendar token
cleared (breaking any standing `.ics` feed URL), and its email rewritten to a
unique, unreachable placeholder (`anonymise-<pk>@invalid`) — freeing the real
address for reuse and guaranteeing the account can no longer log in or be
mailed.

### What's deleted outright

`photos.PersonTag` rows are deleted entirely, in **both** directions — where
this person is tagged in a photo, and where this person tagged someone else —
since a face-identification link is the single most identifying artifact left
once the profile itself is blanked.

### What's kept, but scrubbed

`events.Rsvp` rows are kept, for event-history integrity (attendance counts
stay correct), but each row's free-text `note` field is blanked.

### What's kept untouched

Every authorship/upload relation — publications, documents, photos (uploads
and album creation), comments, présences, events (creation/organisation), and
genealogy records (stories, citations, sources, GEDCOM import references) —
is left exactly as-is, still pointing at the same `Person` row. This is the
"referential integrity preserved" guarantee: a blog post's author list, a
document's uploader, a photo album's creator, etc. never silently lose their
attribution or get reassigned to someone else.

### Interaction with the corbeille (14.5)

Any of the person's rows already sitting in the [corbeille](corbeille.md)
(soft-deleted `BlogPost`/`Document`/`Album`/`Photo`) are **purged immediately**
as part of the same anonymisation transaction, rather than being left
recoverable for the rest of their normal `TRASH_RETENTION_DAYS` window — an
"erased" person's data sitting restorable in the trash for up to 30 more days
would contradict the erasure guarantee.

### Audit trail

The operation logs exactly one `AuditEvent`, with the `ANONYMISE` action,
attributed to the staff member who triggered it — with no old-value payload,
so the audit log itself never becomes a place where the erased identity
survives. See [`audit.md`](audit.md#anonymisation-142) for how
`suppress_generic_audit()` keeps `register_audit()`'s generic per-field
logging from firing a second, PII-carrying event for the same save.

## Consent

A public **privacy notice** page (`confidentialite/`, route name `privacy-notice`,
`PrivacyNoticeView` in `annuaire/views.py`) lists every category from
`PERSONAL_DATA_CATEGORIES` above — reusing the same registry the export builds
from, so the two can't drift apart — alongside five real-world legal facts read
from environment variables (see "Legal facts: environment variables, not
hardcoded" below). The view is decorated `login_not_required`: it must be
readable by a visitor who hasn't signed up yet, and is linked unconditionally
from the sidebar's "Aide" section, visible whether or not the visitor is
logged in.

### What's recorded, and on which model

Acceptance is tracked on `Account`, **not** `Person` — two fields,
`privacy_notice_accepted_at` (nullable timestamp) and `privacy_notice_version`
(the version string that was accepted). This is a deliberate placement:
accepting a notice is an act of the logged-in human at a keyboard, and an
accountless `Person` (a child profile, a deceased ancestor) has no one who
could consent on its behalf. `annuaire/privacy_notice.py`'s `has_accepted(account)`
checks both fields against the current `PRIVACY_NOTICE_VERSION`; `record_acceptance(account)`
sets them and saves.

### Version-bump mechanic

`PRIVACY_NOTICE_VERSION` (`annuaire/privacy_notice.py`) is a plain string, not
semver — `has_accepted()` only ever does an equality check against it, never a
version-ordering comparison. Bumping it whenever the notice's substance
changes immediately makes every member's stored `privacy_notice_version` stop
matching, which brings the acceptance banner back for everyone until they
accept again.

### Acceptance UX: checkbox at signup, banner afterwards — never a hard interstitial

- **`SignupForm`** gains a required `accept_privacy_notice` checkbox; `SignupView.form_valid()`
  calls `record_acceptance()` right after the account is created, so a new
  member is already at the current version from their first login.
- **Existing members** who predate the notice, or whose stored version has
  fallen behind a bump, see a persistent banner (`annuaire/templates/annuaire/base.html`,
  driven by the `show_privacy_notice_banner` context variable) linking to the
  notice and offering a one-click "J'ai lu et j'accepte" button — a `POST` to
  `confidentialite/accepter/` (route name `privacy-notice-accept`,
  `login_required`, POST-only), which calls `record_acceptance(request.user)`
  and redirects back to `home`. There is no hard interstitial that blocks the
  rest of the app until accepted — the banner is dismissed by accepting, not
  by simply navigating away.
- `annuaire.context_processors.privacy_notice_banner` computes
  `show_privacy_notice_banner`: true only for an authenticated user who hasn't
  accepted the current version; always false for an anonymous visitor.

### Legal facts: environment variables, not hardcoded

The notice's real-world legal content — who the data controller is, the
hosting provider and country, a contact address for exercising data-subject
rights, and a plain-language retention summary — comes from five environment
variables (`config/settings.py`, all default `""`): `PRIVACY_CONTROLLER_NAME`,
`PRIVACY_CONTROLLER_CONTACT`, `PRIVACY_HOSTING_PROVIDER`,
`PRIVACY_HOSTING_COUNTRY`, `PRIVACY_RETENTION_SUMMARY`. These are deliberately
**not** hardcoded in a template and **not** an in-app editable field — they're
operational/legal facts about how and where the site is actually hosted, set
once per deployment. Development and tests are fine leaving them empty;
**production must set all five** before launch (see `.env.example` and
[`deployment.md`](deployment.md#environment-variables)).
