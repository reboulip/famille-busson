"""Erasure and anonymisation (14.2) -- a staff flow that blanks a Person's
personal fields while preserving referential integrity: every authorship/
upload FK keeps pointing at this same Person row (their publications survive
under an anonymised author), unlike annuaire/person_merge.py, which moves
relations to a *different* winner Person. Never call into or modify
person_merge.py -- these are two distinct operations.

Written policy on what is retained and why:
- Authorship/upload relations (publications, documents, photos, comments,
  présences, events, genealogy) are KEPT, repointing nothing -- that is the
  entire point of "preserving referential integrity".
- `photos.PersonTag` rows (both where this person is tagged, and where this
  person did the tagging) are DELETED entirely -- a face-identification link
  is the single most identifying artifact left after the profile is blanked.
- `events.Rsvp` rows are KEPT (event-history integrity), but the free-text
  `note` field is blanked.
- Any of this person's soft-deleted (corbeille, 14.5) rows are purged
  immediately -- an "erased" person's data must not sit recoverable in the
  corbeille for up to 30 more days, which would contradict the erasure
  guarantee.
- `export_privacy` is set to REDACT, reusing annuaire/privacy.py's existing
  redaction machinery so every export surface (GEDCOM, Excel, iCal) honours
  the erasure with zero new call sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .audit import record_audit_event
from .models import Account, AuditEvent, Person
from .search.indexing import enqueue_reindex

# Deliberately not a real-sounding name -- must never collide with or
# resemble an actual family member's name. Person.__str__ formats these as
# "{first_name} {last_name}", giving "Personne anonymisée".
ANONYMISED_FIRST_NAME = "Personne"
ANONYMISED_LAST_NAME = "anonymisée"


@dataclass
class AnonymisationReport:
    purged_counts: dict[str, int] = field(default_factory=dict)


def anonymise_person(person: Person, *, actor) -> AnonymisationReport:
    if person.anonymised_at is not None:
        raise ValidationError("Cette personne a déjà été anonymisée.")
    if person.account_id is not None and person.account.is_staff:
        other_active_staff = Account.objects.filter(is_staff=True, is_active=True).exclude(pk=person.account_id)
        if not other_active_staff.exists():
            raise ValidationError("Impossible d'anonymiser le dernier compte actif membre du personnel.")

    report = AnonymisationReport()

    with transaction.atomic():
        person.first_name = ANONYMISED_FIRST_NAME
        person.last_name = ANONYMISED_LAST_NAME
        person.email = None
        person.phone_number = None
        person.postal_address = None
        person.latitude = None
        person.longitude = None
        person.birth_date = None
        person.birth_place = ""
        person.death_date = None
        person.death_place = ""
        person.description = None
        person.profile_photo = None
        person.export_privacy = Person.ExportPrivacy.REDACT
        person.anonymised_at = timezone.now()
        person.save()

        person.owners.clear()

        if person.account_id is not None:
            account = person.account
            account.is_active = False
            account.set_unusable_password()
            account.calendar_token = None
            account.email = f"anonymise-{person.pk}@invalid"
            account.save()

        from photos.models import PersonTag

        PersonTag.objects.filter(Q(person=person) | Q(tagged_by=person)).delete()

        from events.models import Rsvp

        Rsvp.objects.filter(person=person).update(note="")

        report.purged_counts = _purge_trashed_rows(person)

        record_audit_event(
            person,
            action=AuditEvent.Action.ANONYMISE,
            changes={"personne": {"to": "anonymisée"}},
            actor=actor,
        )

    enqueue_reindex(Person, person.pk)
    return report


def _purge_trashed_rows(person: Person) -> dict[str, int]:
    from documents.models import Document
    from photos.models import Album, Photo
    from publications.models import BlogPost

    counts: dict[str, int] = {}

    posts = list(BlogPost.all_objects.filter(authors=person, deleted_at__isnull=False))
    for post in posts:
        post.purge()
    if posts:
        counts["publications.BlogPost"] = len(posts)

    documents = list(
        Document.all_objects.filter(Q(uploaded_by=person) | Q(redactor=person), deleted_at__isnull=False).distinct()
    )
    for document in documents:
        document.purge()
    if documents:
        counts["documents.Document"] = len(documents)

    albums = list(Album.all_objects.filter(created_by=person, deleted_at__isnull=False))
    for album in albums:
        album.purge()
    if albums:
        counts["photos.Album"] = len(albums)

    photos = list(Photo.all_objects.filter(uploaded_by=person, deleted_at__isnull=False))
    for photo in photos:
        photo.purge()
    if photos:
        counts["photos.Photo"] = len(photos)

    return counts
