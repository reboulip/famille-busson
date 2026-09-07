"""Background-queue task wrapper (9.7) -- publications.tasks."""

import pytest
from django.core import mail

from publications.models import BlogPost
from publications.tasks import send_blog_post_notification


@pytest.mark.django_db
def test_sends_the_notification(other_person):
    post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
    post.authors.add(other_person)

    send_blog_post_notification(post.pk, "alice@example.com")

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ["alice@example.com"]
    assert post.title in sent.subject
    assert str(other_person) in sent.alternatives[0][0]


@pytest.mark.django_db
def test_a_deleted_post_is_skipped_without_raising(db):
    # Retrying a task for a post that no longer exists would never succeed --
    # this must not raise (which would trigger django-q2 to keep retrying).
    send_blog_post_notification(999999, "alice@example.com")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_a_send_failure_raises_for_django_q2_to_retry(other_person, monkeypatch):
    import publications.tasks as tasks_module

    def _raise(*args, **kwargs):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(tasks_module, "send_one_email", _raise)

    post = BlogPost.objects.create(title="Nouvelle publication", body="Du contenu.")
    post.authors.add(other_person)

    with pytest.raises(RuntimeError):
        send_blog_post_notification(post.pk, "alice@example.com")
