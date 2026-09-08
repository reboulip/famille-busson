import pytest
from django.core import mail

from annuaire.email_utils import OutgoingEmail, send_bulk_emails, send_one_email


@pytest.mark.django_db
def test_send_one_email_sends_it():
    send_one_email(OutgoingEmail(to="alice@example.com", subject="Sujet", text_body="Contenu"))
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["alice@example.com"]


@pytest.mark.django_db
def test_send_one_email_raises_on_failure(monkeypatch):
    import annuaire.email_utils as email_utils

    def _raise(*args, **kwargs):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(email_utils, "build_message", _raise)

    with pytest.raises(RuntimeError):
        send_one_email(OutgoingEmail(to="alice@example.com", subject="Sujet", text_body="Contenu"))


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

    real_build_message = email_utils.build_message

    # Was a patch of email_utils.send_mail; messages are now built as
    # EmailMultiAlternatives so they can carry an HTML half and inline images.
    def _flaky_build_message(email, connection=None):
        if email.to == "bad@example.com":
            raise Exception("SMTP down")
        return real_build_message(email, connection=connection)

    monkeypatch.setattr(email_utils, "build_message", _flaky_build_message)

    messages = [
        ("good1@example.com", "Sujet", "Contenu"),
        ("bad@example.com", "Sujet", "Contenu"),
        ("good2@example.com", "Sujet", "Contenu"),
    ]
    sent, failed = send_bulk_emails(messages)

    assert sent == ["good1@example.com", "good2@example.com"]
    assert failed == ["bad@example.com"]
    assert len(mail.outbox) == 2
