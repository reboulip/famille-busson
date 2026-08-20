import pytest
from django.core import mail

from annuaire.email_utils import send_bulk_emails


@pytest.mark.django_db
def test_send_bulk_emails_sends_all_messages():
    messages = [(f"user{i}@example.com", "Sujet", "Contenu") for i in range(3)]
    sent, failed = send_bulk_emails(messages)
    assert sent == [m[0] for m in messages]
    assert failed == []
    assert len(mail.outbox) == 3


@pytest.mark.django_db
def test_send_bulk_emails_isolates_a_failed_send(monkeypatch):
    import annuaire.email_utils as email_utils

    real_send_mail = email_utils.send_mail

    def _flaky_send_mail(subject, body, from_email, recipient_list, **kwargs):
        if recipient_list == ["bad@example.com"]:
            raise Exception("SMTP down")
        return real_send_mail(subject, body, from_email, recipient_list, **kwargs)

    monkeypatch.setattr(email_utils, "send_mail", _flaky_send_mail)

    messages = [
        ("good1@example.com", "Sujet", "Contenu"),
        ("bad@example.com", "Sujet", "Contenu"),
        ("good2@example.com", "Sujet", "Contenu"),
    ]
    sent, failed = send_bulk_emails(messages)

    assert sent == ["good1@example.com", "good2@example.com"]
    assert failed == ["bad@example.com"]
    assert len(mail.outbox) == 2
