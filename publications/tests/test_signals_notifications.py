import pytest
from django.core import mail

from publications.models import BlogPost


@pytest.mark.django_db
def test_new_blog_post_notifies_subscribed_users(person, other_person):
    person.settings.notify_on_new_blog_post = True
    person.settings.save()

    post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
    post.authors.add(other_person)

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [person.email]
    assert post.title in sent.subject


@pytest.mark.django_db
def test_new_blog_post_does_not_notify_unsubscribed_users(person, other_person):
    post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
    post.authors.add(other_person)

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_blog_post_update_does_not_resend_notification(person, other_person):
    person.settings.notify_on_new_blog_post = True
    person.settings.save()

    post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
    post.authors.add(other_person)
    assert len(mail.outbox) == 1

    post.title = "Titre modifié"
    post.save()
    assert len(mail.outbox) == 1
