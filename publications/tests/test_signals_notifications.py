import pytest
from django.core import mail

from publications.models import BlogPost


@pytest.mark.django_db
def test_new_blog_post_notifies_subscribed_users(person, other_person, django_capture_on_commit_callbacks):
    person.settings.notify_on_new_blog_post = True
    person.settings.save()
    other_person.settings.notify_on_new_blog_post = False
    other_person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
        post.authors.add(other_person)

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [person.email]
    assert post.title in sent.subject


@pytest.mark.django_db
def test_new_blog_post_notification_includes_the_author_byline(
    person, other_person, django_capture_on_commit_callbacks
):
    """Regression: post_save fires before form.save_m2m() adds the authors, so the
    notification must be built after commit or the byline is always empty."""
    person.settings.notify_on_new_blog_post = True
    person.settings.save()
    other_person.settings.notify_on_new_blog_post = False
    other_person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
        post.authors.add(other_person)

    assert len(mail.outbox) == 1
    assert str(other_person) in mail.outbox[0].alternatives[0][0]


@pytest.mark.django_db
def test_new_blog_post_does_not_notify_unsubscribed_users(person, other_person, django_capture_on_commit_callbacks):
    person.settings.notify_on_new_blog_post = False
    person.settings.save()
    other_person.settings.notify_on_new_blog_post = False
    other_person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
        post.authors.add(other_person)

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_new_blog_post_does_not_notify_deceased_subscriber(person, other_person, django_capture_on_commit_callbacks):
    person.deceased = True
    person.save()
    person.settings.notify_on_new_blog_post = True
    person.settings.save()
    other_person.settings.notify_on_new_blog_post = False
    other_person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
        post.authors.add(other_person)

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_blog_post_update_does_not_resend_notification(person, other_person, django_capture_on_commit_callbacks):
    person.settings.notify_on_new_blog_post = True
    person.settings.save()
    other_person.settings.notify_on_new_blog_post = False
    other_person.settings.save()

    with django_capture_on_commit_callbacks(execute=True):
        post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
        post.authors.add(other_person)
    assert len(mail.outbox) == 1

    with django_capture_on_commit_callbacks(execute=True):
        post.title = "Titre modifié"
        post.save()
    assert len(mail.outbox) == 1
