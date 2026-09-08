import datetime

import pytest
from django.db import IntegrityError

from genealogy.models import Story, StoryPhoto


@pytest.mark.django_db
def test_story_str_is_title(story):
    assert str(story) == "Le voyage en Bretagne"


@pytest.mark.django_db
def test_chronological_orders_by_date_ascending(person):
    later = Story.objects.create(person=person, title="Plus tard", date=datetime.date(2000, 1, 1))
    earlier = Story.objects.create(person=person, title="Plus tôt", date=datetime.date(1990, 1, 1))
    assert list(Story.objects.chronological()) == [earlier, later]


@pytest.mark.django_db
def test_chronological_sorts_undated_stories_last(person):
    dated = Story.objects.create(person=person, title="Daté", date=datetime.date(1990, 1, 1))
    undated = Story.objects.create(person=person, title="Non daté")
    assert list(Story.objects.chronological()) == [dated, undated]


@pytest.mark.django_db
def test_story_photo_unique_constraint(story, photo):
    StoryPhoto.objects.create(story=story, photo=photo)
    with pytest.raises(IntegrityError):
        StoryPhoto.objects.create(story=story, photo=photo)


@pytest.mark.django_db
def test_story_photo_str(story, photo):
    story_photo = StoryPhoto.objects.create(story=story, photo=photo)
    assert str(photo) in str(story_photo)
    assert str(story) in str(story_photo)
