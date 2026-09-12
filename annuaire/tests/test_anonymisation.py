import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from annuaire.anonymisation import anonymise_person
from annuaire.models import AuditEvent, Person
from documents.models import Category, Document
from events.models import Event, Rsvp
from photos.models import Album, PersonTag, Photo
from publications.models import BlogPost


@pytest.fixture(autouse=True)
def use_tmp_media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.DOCUMENTS_ROOT = tmp_path / "documents_data"
    settings.PHOTOS_ROOT = tmp_path / "documents_data" / "photos"


def _uploaded_image(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name=name, content=buffer.getvalue(), content_type="image/png")


@pytest.mark.django_db
def test_anonymise_blanks_personal_fields(person):
    anonymise_person(person, actor=None)
    person.refresh_from_db()
    assert person.first_name == "Personne"
    assert person.last_name == "anonymisée"
    assert person.email is None
    assert person.phone_number is None
    assert person.postal_address is None
    assert person.birth_date is None
    assert person.birth_place == ""
    assert person.description is None
    assert person.export_privacy == Person.ExportPrivacy.REDACT
    assert person.anonymised_at is not None


@pytest.mark.django_db
def test_anonymise_deactivates_linked_account(person, account):
    anonymise_person(person, actor=None)
    account.refresh_from_db()
    assert account.is_active is False
    assert not account.has_usable_password()
    assert account.calendar_token is None
    assert account.email == f"anonymise-{person.pk}@invalid"


@pytest.mark.django_db
def test_anonymise_clears_owners(accountless_person, person):
    accountless_person.owners.add(person)
    anonymise_person(accountless_person, actor=None)
    assert accountless_person.owners.count() == 0


@pytest.mark.django_db
def test_anonymise_deletes_person_tags(person, other_person):
    album = Album.objects.create(title="Vacances")
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)
    PersonTag.objects.create(photo=photo, person=other_person, tagged_by=person)

    anonymise_person(person, actor=None)

    assert not PersonTag.objects.filter(person=person).exists()
    assert not PersonTag.objects.filter(tagged_by=person).exists()


@pytest.mark.django_db
def test_anonymise_blanks_rsvp_note_but_keeps_rsvp(person):
    event = Event.objects.create(title="Fête", start=timezone.now())
    rsvp = Rsvp.objects.create(event=event, person=person, response="yes", note="Sans gluten")

    anonymise_person(person, actor=None)

    rsvp.refresh_from_db()
    assert rsvp.note == ""
    assert Rsvp.objects.filter(pk=rsvp.pk, person=person).exists()


@pytest.mark.django_db
def test_anonymise_keeps_authorship_relations(person):
    post = BlogPost.objects.create(title="Titre", body="Contenu")
    post.authors.add(person)

    anonymise_person(person, actor=None)

    assert post.authors.filter(pk=person.pk).exists()


@pytest.mark.django_db
def test_anonymise_purges_trashed_rows(person, account):
    category = Category.objects.create(name="Actes")
    document = Document.objects.create(title="Doc", category=category, uploaded_by=person)
    document.soft_delete(account)

    anonymise_person(person, actor=account)

    assert not Document.all_objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_anonymise_logs_audit_event(person, account):
    AuditEvent.objects.all().delete()
    anonymise_person(person, actor=account)
    # The field-level UPDATE from register_audit(Person, ...) also fires
    # (many tracked fields change) -- the ANONYMISE event is the one this
    # operation adds explicitly.
    event = AuditEvent.objects.get(
        content_type__model="person", object_id=str(person.pk), action=AuditEvent.Action.ANONYMISE
    )
    assert event.actor_id == account.pk


@pytest.mark.django_db
def test_anonymise_twice_raises_validation_error(person):
    anonymise_person(person, actor=None)
    with pytest.raises(ValidationError):
        anonymise_person(person, actor=None)


@pytest.mark.django_db
def test_cannot_anonymise_last_active_staff_account(staff_account):
    staff_person = Person.objects.create(first_name="Staff", last_name="Only", email="staff@example.com")
    staff_person.account = staff_account
    staff_person.save()

    with pytest.raises(ValidationError):
        anonymise_person(staff_person, actor=None)


@pytest.mark.django_db
def test_person_merge_still_works_after_anonymisation_item(person, accountless_person):
    # Guard against the two operations getting entangled: merge_persons()
    # must remain untouched by this item.
    from annuaire.person_merge import merge_persons

    report = merge_persons(person, accountless_person)
    assert not Person.objects.filter(pk=accountless_person.pk).exists()
    assert report.dropped
