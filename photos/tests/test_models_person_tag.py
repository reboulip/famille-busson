import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from photos.models import PersonTag

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_str_includes_person_and_photo(photo, person):
    tag = PersonTag.objects.create(photo=photo, person=person)
    assert str(person) in str(tag)


@pytest.mark.django_db
def test_unique_constraint_one_tag_per_person_per_photo(photo, person):
    PersonTag.objects.create(photo=photo, person=person)
    with pytest.raises(IntegrityError):
        PersonTag.objects.create(photo=photo, person=person)


@pytest.mark.django_db
def test_region_box_all_four_fields_is_valid(photo, person):
    tag = PersonTag(photo=photo, person=person, region_x=0.1, region_y=0.2, region_width=0.3, region_height=0.4)
    tag.full_clean()  # does not raise


@pytest.mark.django_db
def test_region_box_none_of_the_fields_is_valid(photo, person):
    tag = PersonTag(photo=photo, person=person)
    tag.full_clean()  # does not raise


@pytest.mark.django_db
def test_region_box_partial_fields_is_rejected(photo, person):
    tag = PersonTag(photo=photo, person=person, region_x=0.1, region_y=0.2)
    with pytest.raises(ValidationError):
        tag.full_clean()


@pytest.mark.django_db
def test_deleting_photo_cascades_tags(album, person):
    photo = album.photos.create(file=make_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)
    photo.delete()
    assert not PersonTag.objects.exists()


@pytest.mark.django_db
def test_tagged_by_records_who_tagged(photo, person, other_person):
    tag = PersonTag.objects.create(photo=photo, person=person, tagged_by=other_person)
    assert tag.tagged_by == other_person
