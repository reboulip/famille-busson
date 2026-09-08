"""11.5 -- ActivityFeedView."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from publications.models import BlogPost

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_activity_feed_requires_login(client):
    response = client.get(reverse("activity-feed"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_first_visit_uses_thirty_day_window(auth_client, person):
    assert person.account.last_feed_seen_at is None
    old_post = BlogPost.objects.create(title="Il y a longtemps", body="x")
    old_post.authors.add(person)
    BlogPost.objects.filter(pk=old_post.pk).update(created_at=timezone.now() - datetime.timedelta(days=90))
    recent_post = BlogPost.objects.create(title="Récent", body="y")
    recent_post.authors.add(person)

    response = auth_client.get(reverse("activity-feed"))

    recent_items = [e.item for e in response.context["recent_entries"]]
    assert recent_post in recent_items
    assert old_post not in recent_items


@pytest.mark.django_db
def test_visiting_stamps_last_feed_seen_at(auth_client, person):
    auth_client.get(reverse("activity-feed"))

    person.account.refresh_from_db()
    assert person.account.last_feed_seen_at is not None


@pytest.mark.django_db
def test_current_visit_still_shows_items_despite_stamping(auth_client, person):
    post = BlogPost.objects.create(title="Maintenant", body="x")
    post.authors.add(person)

    response = auth_client.get(reverse("activity-feed"))

    assert post in [e.item for e in response.context["recent_entries"]]


@pytest.mark.django_db
def test_second_visit_uses_last_feed_seen_at_as_cutoff(auth_client, person):
    from annuaire.models import Account

    Account.objects.filter(pk=person.account.pk).update(last_feed_seen_at=timezone.now() - datetime.timedelta(days=1))
    old_post = BlogPost.objects.create(title="Avant la dernière visite", body="x")
    old_post.authors.add(person)
    BlogPost.objects.filter(pk=old_post.pk).update(created_at=timezone.now() - datetime.timedelta(days=5))

    response = auth_client.get(reverse("activity-feed"))

    assert old_post not in [e.item for e in response.context["recent_entries"]]


@pytest.mark.django_db
def test_empty_feed_shows_onboarding_empty_state(auth_client, person):
    # No other activity exists, and activity_since() excludes the viewer's
    # own profile-join event from their own feed -- so this is genuinely empty.
    response = auth_client.get(reverse("activity-feed"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Rien à signaler pour l" in content
