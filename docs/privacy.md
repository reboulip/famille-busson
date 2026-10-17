# Vie privée et traçabilité

This page covers the privacy features:

- personal data export;
- erasure (anonymisation) of a person;
- the privacy notice and its acceptance.

Two related features have their own pages: the [audit log](audit.md) and the
[trash (corbeille)](corbeille.md).

## Personal data export

Anyone who can edit a profile can download a `.zip` file with everything the site holds
about that person. The button "Télécharger mes données" is on the profile page, next to
"Modifier le profil". The URL is `personne/<id>/donnees/`.

"Anyone who can edit a profile" means: the person themself, staff, or an owner of a
profile with no account (see [`permissions.md`](permissions.md)).

The `.zip` file contains:

- `donnees.json` — the data, grouped by category (see below);
- `LISEZ-MOI.txt` — a short explanation in French, with the number of items in each
  category;
- the profile photo (`photo-profil.<ext>`), if there is one.

### Scope: metadata and links only, one exception

The export lists information and links to pages in the site. It does not include the
files themselves. For example, a document is a link to its page, not the PDF. **The
profile photo is the only exception**: it is included in the `.zip`, because it is the
person's own small image.

### Access model: scoped through the viewer, not the subject

The export only contains what the **person who downloads it** is allowed to see. It
never shows more than the rest of the site would. For example:

- a staff member who exports a member's data still does not see documents in a
  category that staff cannot open;
- a parent who exports a child's data does not see albums restricted to a group the
  parent is not in.

### Personal data categories

| Key | Label | Covers |
|---|---|---|
| `profil` | Profil | Profile fields: name, contact details, address, birth and death details, description, export privacy choice, whether there is a photo, creation date, link to the profile. |
| `relations_familiales` | Relations familiales | Family relations (parent, child, spouse), with dates. |
| `comptes_geres` | Comptes gérés | Profiles this person owns, and the owners of this profile. |
| `parametres` | Préférences de notification | Email notification settings. |
| `places` | Résidences | Houses this person owns. |
| `presences` | Présences | This person's stays in houses. |
| `publications` | Publications | Blog posts this person wrote. |
| `commentaires` | Commentaires | Comments this person wrote, with a short extract and a link to the post. |
| `documents` | Documents | Documents this person uploaded or wrote. |
| `photos` | Photos | Albums created, photos uploaded, photos where this person appears, and people this person identified in photos. |
| `evenements` | Événements | Events this person created or organises, and their answers to events. |
| `genealogie` | Généalogie | Life stories about or by this person, sources and citations, and GEDCOM imports involving this person. |
| `consentements` | Consentements | When the account accepted the privacy notice, and which version. |

A test checks that every link from another table to a person is covered by the export.
If you add a new link to `Person`, you must add it to `annuaire/personal_data.py`.

## Retention and erasure policy

Staff can **anonymise** a person with the "Anonymiser" button on the profile page. This
erases the person's identity for good. It cannot be undone, and it cannot be done twice.
The site refuses to anonymise the last active staff account.

The person's profile is not deleted: it stays, but empty. So everything the person
wrote or uploaded keeps its link to the (now anonymous) profile. Nothing is given to
another profile.

### What's blanked

On the profile: the name becomes "Personne anonymisée". The email, phone, address, map
coordinates, birth and death details, description and photo are erased. The export
privacy choice becomes "redact", so the person is hidden in all exports (GEDCOM, Excel,
calendar). The list of owners is emptied.

If the person has an account, the account is disabled. Its password and calendar link
stop working. Its email is replaced by a fake address (`anonymise-<id>@invalid`), so the
real address can be used again, and the account can never log in or receive emails.

### What's deleted outright

All photo identifications are deleted: the photos where this person was identified,
and the people this person identified in photos. A face linked to a name is very
identifying.

### What's kept, but scrubbed

Answers to events are kept, so attendance numbers stay correct. But the free-text
comment on each answer is erased.

### What's kept untouched

Everything the person created stays as it was: posts, documents, photos, albums,
comments, stays, events, stories, sources. It still shows the same (now anonymous)
author.

### Interaction with the corbeille (14.5)

Anything the person had put in the [trash](corbeille.md) is deleted for good at once,
without waiting 30 days. Otherwise, the data of an "erased" person could still be
restored.

### Audit trail

Anonymisation writes one entry in the audit log, with the name of the staff member who
did it. This entry does not contain the old values, so the erased identity is not kept
in the log. See [`audit.md`](audit.md#anonymisation-142).

## Consent

The **privacy notice** (`confidentialite/`) lists the same data categories as the
export, and five legal facts set in environment variables (see below). Anyone can read
it, even without an account. It is linked from the "Aide" section of the menu.

### What's recorded, and on which model

Acceptance is saved on the **account**, not on the profile: the date of acceptance and
the version accepted. Only a person who logs in can accept. A profile with no account
(a child, an ancestor) has no one who can accept for it.

### Version-bump mechanic

The current version of the notice is `PRIVACY_NOTICE_VERSION`, in
`annuaire/privacy_notice.py`. It is a simple text value. When the content of the notice
changes, change this value. Then every member must accept the notice again.

### Acceptance UX: checkbox at signup, banner afterwards — never a hard interstitial

- **At signup**, the form has a required checkbox to accept the notice.
- **Existing members** who have not accepted the current version see a banner at the top
  of every page. It has a link to the notice and a button "J'ai lu et j'accepte". The
  banner goes away only when they accept. They can still use the site in the meantime.

### Legal facts: environment variables, not hardcoded

Five environment variables hold the legal facts shown on the notice:

| Variable | Meaning |
|---|---|
| `PRIVACY_CONTROLLER_NAME` | Who is responsible for the data. |
| `PRIVACY_CONTROLLER_CONTACT` | The contact address for data requests. |
| `PRIVACY_HOSTING_PROVIDER` | The hosting company. |
| `PRIVACY_HOSTING_COUNTRY` | The hosting country. |
| `PRIVACY_RETENTION_SUMMARY` | A short, plain explanation of how long data is kept. |

They are environment variables, not site settings, because they describe how the site
is really hosted. They are set once per installation. They can stay empty in
development and tests. **In production, all five must be set** (see
[`deployment.md`](deployment.md#environment-variables)).
