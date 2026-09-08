import datetime
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from annuaire.models import Person, Relation
from annuaire.person_merge import (
    HANDLED_HIDDEN_RELATIONS,
    HANDLED_RELATIONS,
    find_duplicate_candidates,
    merge_persons,
)
from documents.models import Category, Document
from events.models import Event, Rsvp
from genealogy.models import Citation, Source, Story
from photos.models import Album, PersonTag, Photo
from publications.models import BlogPost, Comment


@pytest.fixture(autouse=True)
def use_tmp_media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.DOCUMENTS_ROOT = tmp_path / "documents_data"
    settings.PHOTOS_ROOT = tmp_path / "documents_data" / "photos"


def _uploaded_image():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name="photo.png", content=buffer.getvalue(), content_type="image/png")


# --- Meta-guard: fails if a future FK/M2M onto Person escapes the merge ----


def test_person_meta_guard_covers_every_relation():
    for f in Person._meta.get_fields(include_hidden=True):
        if not (f.is_relation and f.auto_created and not f.concrete):
            continue
        if f.related_model._meta.auto_created:
            continue  # the auto-created through table of a plain M2M
        if getattr(f, "hidden", False):
            key = (f.related_model._meta.app_label, f.related_model._meta.model_name, f.field.name)
            assert key in HANDLED_HIDDEN_RELATIONS, f"unhandled hidden relation: {key}"
        else:
            accessor = f.get_accessor_name()
            assert accessor in HANDLED_RELATIONS, f"unhandled relation: {accessor}"

    for f in Person._meta.many_to_many:
        assert f.name in HANDLED_RELATIONS, f"unhandled forward M2M: {f.name}"


# --- Duplicate detection -----------------------------------------------


@pytest.mark.django_db
def test_find_duplicates_matches_identical_name():
    Person.objects.create(first_name="Jean", last_name="Busson")
    Person.objects.create(first_name="Jean", last_name="Busson")
    candidates = find_duplicate_candidates()
    assert len(candidates) == 1
    assert candidates[0].reason == "Nom et prénom identiques"


@pytest.mark.django_db
def test_find_duplicates_matches_accent_insensitively():
    Person.objects.create(first_name="Élise", last_name="Büsson")
    Person.objects.create(first_name="Elise", last_name="Busson")
    candidates = find_duplicate_candidates()
    assert len(candidates) == 1


@pytest.mark.django_db
def test_find_duplicates_matches_same_lastname_and_birthdate():
    Person.objects.create(first_name="Jean", last_name="Busson", birth_date=datetime.date(1950, 1, 1))
    Person.objects.create(first_name="Jeannot", last_name="Busson", birth_date=datetime.date(1950, 1, 1))
    candidates = find_duplicate_candidates()
    assert any(c.reason == "Même nom et même date de naissance" for c in candidates)


@pytest.mark.django_db
def test_find_duplicates_matches_identical_email():
    Person.objects.create(first_name="Jean", last_name="Busson", email="jean@example.com")
    Person.objects.create(first_name="Jeanne", last_name="Autre", email="jean@example.com")
    candidates = find_duplicate_candidates()
    assert any(c.reason == "Adresse email identique" for c in candidates)


@pytest.mark.django_db
def test_find_duplicates_ignores_unrelated_people(person, other_person):
    assert find_duplicate_candidates() == []


# --- Core merge behaviour -------------------------------------------------


@pytest.mark.django_db
def test_merge_refuses_self_merge(person):
    with pytest.raises(ValidationError):
        merge_persons(person, person)


@pytest.mark.django_db
def test_merge_refuses_when_both_have_accounts(person, other_person):
    with pytest.raises(ValidationError):
        merge_persons(person, other_person)


@pytest.mark.django_db
def test_merge_deletes_the_loser(person, accountless_person):
    merge_persons(person, accountless_person)
    assert not Person.objects.filter(pk=accountless_person.pk).exists()
    assert Person.objects.filter(pk=person.pk).exists()


@pytest.mark.django_db
def test_merge_fills_blank_winner_fields_from_loser(person, accountless_person):
    accountless_person.phone_number = "0600000000"
    accountless_person.save()
    merge_persons(person, accountless_person)
    person.refresh_from_db()
    assert person.phone_number == "0600000000"


@pytest.mark.django_db
def test_merge_keeps_winner_value_by_default_when_both_set(person, accountless_person):
    person.phone_number = "0611111111"
    person.save()
    accountless_person.phone_number = "0622222222"
    accountless_person.save()
    merge_persons(person, accountless_person)
    person.refresh_from_db()
    assert person.phone_number == "0611111111"


@pytest.mark.django_db
def test_merge_field_choice_can_take_losers_value(person, accountless_person):
    person.phone_number = "0611111111"
    person.save()
    accountless_person.phone_number = "0622222222"
    accountless_person.save()
    merge_persons(person, accountless_person, field_choices={"phone_number": 2})
    person.refresh_from_db()
    assert person.phone_number == "0622222222"


@pytest.mark.django_db
def test_merge_field_choice_can_explicitly_keep_winners_value(person, accountless_person):
    person.phone_number = "0611111111"
    person.save()
    accountless_person.phone_number = "0622222222"
    accountless_person.save()
    merge_persons(person, accountless_person, field_choices={"phone_number": 1})
    person.refresh_from_db()
    assert person.phone_number == "0611111111"


@pytest.mark.django_db
def test_merge_moves_loser_account_when_winner_has_none(accountless_person, other_person):
    loser_account = other_person.account
    merge_persons(accountless_person, other_person)
    accountless_person.refresh_from_db()
    assert accountless_person.account_id == loser_account.pk


@pytest.mark.django_db
def test_merge_reassigns_profile_photo_before_deleting_loser(person, accountless_person):
    accountless_person.profile_photo = _uploaded_image()
    accountless_person.save()
    photo_name = accountless_person.profile_photo.name

    merge_persons(person, accountless_person)

    person.refresh_from_db()
    assert person.profile_photo.name == photo_name
    assert person.profile_photo.storage.exists(photo_name)


# --- Relations, including the self-relation recursion guard ---------------


@pytest.mark.django_db
def test_merge_repoints_relation_to_a_third_person(person, accountless_person, other_person):
    loser_pk = accountless_person.pk
    Relation.objects.create(person1=accountless_person, person2=other_person, relationship_type=2)
    merge_persons(person, accountless_person)
    assert Relation.objects.filter(person1=person, person2=other_person, relationship_type=2).exists()
    assert Relation.objects.filter(person1=other_person, person2=person, relationship_type=3).exists()
    assert not Relation.objects.filter(person1_id=loser_pk).exists()
    assert not Relation.objects.filter(person2_id=loser_pk).exists()


@pytest.mark.django_db
def test_merge_does_not_duplicate_a_relation_already_shared_with_winner(person, accountless_person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    Relation.objects.create(person1=accountless_person, person2=other_person, relationship_type=2)
    merge_persons(person, accountless_person)
    assert Relation.objects.filter(person1=person, person2=other_person).count() == 1


@pytest.mark.django_db
def test_merge_two_people_who_are_parent_and_child_does_not_recurse(person, accountless_person):
    # accountless_person is person's parent -- exactly the false positive
    # name-based duplicate detection is most likely to surface. This must not
    # produce a self-Relation (which would send create_inverse_relation into
    # infinite recursion) -- the edge is dropped instead.
    Relation.objects.create(person1=person, person2=accountless_person, relationship_type=2)
    merge_persons(person, accountless_person)
    assert not Relation.objects.filter(person1=person, person2=person).exists()
    assert Relation.objects.count() == 0


# --- Unique-together constraint handling (PersonTag, Rsvp) -----------------


@pytest.mark.django_db
def test_merge_repoints_person_tag_when_winner_has_none(person, accountless_person):
    album = Album.objects.create(title="Album")
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    tag = PersonTag.objects.create(photo=photo, person=accountless_person)

    merge_persons(person, accountless_person)

    tag.refresh_from_db()
    assert tag.person_id == person.pk


@pytest.mark.django_db
def test_merge_drops_duplicate_person_tag_when_winner_already_tagged(person, accountless_person):
    album = Album.objects.create(title="Album")
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)
    loser_tag = PersonTag.objects.create(photo=photo, person=accountless_person)

    merge_persons(person, accountless_person)

    assert not PersonTag.objects.filter(pk=loser_tag.pk).exists()
    assert PersonTag.objects.filter(photo=photo, person=person).count() == 1


@pytest.mark.django_db
def test_merge_repoints_rsvp_when_winner_has_none(person, accountless_person):
    event = Event.objects.create(
        title="Réunion", start=timezone.now(), end=timezone.now() + datetime.timedelta(hours=1)
    )
    rsvp = Rsvp.objects.create(event=event, person=accountless_person, response="oui")

    merge_persons(person, accountless_person)

    rsvp.refresh_from_db()
    assert rsvp.person_id == person.pk


@pytest.mark.django_db
def test_merge_drops_duplicate_rsvp_when_winner_already_responded(person, accountless_person):
    event = Event.objects.create(
        title="Réunion", start=timezone.now(), end=timezone.now() + datetime.timedelta(hours=1)
    )
    Rsvp.objects.create(event=event, person=person, response="oui")
    loser_rsvp = Rsvp.objects.create(event=event, person=accountless_person, response="non")

    merge_persons(person, accountless_person)

    assert not Rsvp.objects.filter(pk=loser_rsvp.pk).exists()
    assert Rsvp.objects.filter(event=event, person=person).count() == 1


# --- Plain M2M and simple FK repoints --------------------------------------


@pytest.mark.django_db
def test_merge_moves_blog_post_authorship(person, accountless_person):
    post = BlogPost.objects.create(title="Titre", body="Texte")
    post.authors.add(accountless_person)
    merge_persons(person, accountless_person)
    assert person in post.authors.all()


@pytest.mark.django_db
def test_merge_moves_chalet_ownership(person, accountless_person):
    from annuaire.models import Chalet

    chalet = Chalet.objects.create(name="Chalet", address="1 rue des Alpes")
    chalet.owners.add(accountless_person)
    merge_persons(person, accountless_person)
    assert person in chalet.owners.all()


@pytest.mark.django_db
def test_merge_moves_event_organiser(person, accountless_person):
    event = Event.objects.create(
        title="Réunion", start=timezone.now(), end=timezone.now() + datetime.timedelta(hours=1)
    )
    event.organisers.add(accountless_person)
    merge_persons(person, accountless_person)
    assert person in event.organisers.all()


@pytest.mark.django_db
def test_merge_repoints_comment_author(person, accountless_person):
    post = BlogPost.objects.create(title="Titre", body="Texte")
    comment = Comment.objects.create(post=post, author=accountless_person, body="x")
    merge_persons(person, accountless_person)
    comment.refresh_from_db()
    assert comment.author_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_document_uploaded_by_and_redactor(person, accountless_person):
    category = Category.objects.create(name="Divers")
    document = Document.objects.create(
        title="Acte", category=category, uploaded_by=accountless_person, redactor=accountless_person
    )
    merge_persons(person, accountless_person)
    document.refresh_from_db()
    assert document.uploaded_by_id == person.pk
    assert document.redactor_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_album_created_by(person, accountless_person):
    album = Album.objects.create(title="Album", created_by=accountless_person)
    merge_persons(person, accountless_person)
    album.refresh_from_db()
    assert album.created_by_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_photo_uploaded_by(person, accountless_person):
    album = Album.objects.create(title="Album")
    photo = Photo.objects.create(album=album, file=_uploaded_image(), uploaded_by=accountless_person)
    merge_persons(person, accountless_person)
    photo.refresh_from_db()
    assert photo.uploaded_by_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_person_tag_tagged_by(person, accountless_person, other_person):
    album = Album.objects.create(title="Album")
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    tag = PersonTag.objects.create(photo=photo, person=other_person, tagged_by=accountless_person)
    merge_persons(person, accountless_person)
    tag.refresh_from_db()
    assert tag.tagged_by_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_story_person_and_created_by(person, accountless_person):
    story = Story.objects.create(person=accountless_person, title="Récit", created_by=accountless_person)
    merge_persons(person, accountless_person)
    story.refresh_from_db()
    assert story.person_id == person.pk
    assert story.created_by_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_source_created_by(person, accountless_person):
    source = Source.objects.create(title="Acte", created_by=accountless_person)
    merge_persons(person, accountless_person)
    source.refresh_from_db()
    assert source.created_by_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_citation_person(person, accountless_person):
    source = Source.objects.create(title="Acte")
    citation = Citation.objects.create(source=source, person=accountless_person, claim="birth_date")
    merge_persons(person, accountless_person)
    citation.refresh_from_db()
    assert citation.person_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_gedcom_import_uploaded_by(person, accountless_person):
    from genealogy.models import GedcomImport

    gedcom_import = GedcomImport.objects.create(uploaded_by=accountless_person, raw_content="0 HEAD\n0 TRLR\n")
    merge_persons(person, accountless_person)
    gedcom_import.refresh_from_db()
    assert gedcom_import.uploaded_by_id == person.pk


@pytest.mark.django_db
def test_merge_repoints_staged_individual_match_and_created_person(person, accountless_person):
    from genealogy.models import GedcomImport, StagedIndividual

    gedcom_import = GedcomImport.objects.create(raw_content="0 HEAD\n0 TRLR\n")
    staged = StagedIndividual.objects.create(
        gedcom_import=gedcom_import, match_person=accountless_person, created_person=accountless_person
    )
    merge_persons(person, accountless_person)
    staged.refresh_from_db()
    assert staged.match_person_id == person.pk
    assert staged.created_person_id == person.pk


# --- Self-referential owners M2M -------------------------------------------


@pytest.mark.django_db
def test_merge_moves_owners_of_the_loser(person, accountless_person, other_person):
    accountless_person.owners.add(other_person)
    merge_persons(person, accountless_person)
    assert other_person in person.owners.all()


@pytest.mark.django_db
def test_merge_moves_profiles_managed_by_the_loser(person, accountless_person):
    managed = Person.objects.create(first_name="Charlotte", last_name="Busson")
    managed.owners.add(accountless_person)
    merge_persons(person, accountless_person)
    managed.refresh_from_db()
    assert person in managed.owners.all()


@pytest.mark.django_db
def test_merge_never_leaves_winner_owning_itself(person, accountless_person):
    accountless_person.owners.add(person)
    merge_persons(person, accountless_person)
    assert person not in person.owners.all()
