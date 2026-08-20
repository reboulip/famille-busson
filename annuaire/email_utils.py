import logging

from django.conf import settings
from django.core.mail import get_connection, send_mail

logger = logging.getLogger("django")

# A fresh SMTP connection per email pushed large batches past the provider's timeout
# (see BulkAccountCreateView, annuaire/views.py). Reuse one connection across a batch,
# cycling it periodically so a long-lived connection doesn't itself get dropped.
EMAILS_PER_CONNECTION = 15


def send_bulk_emails(messages):
    """Send (email, subject, body) tuples over a shared, periodically-cycled SMTP
    connection. Best-effort per recipient: one failure doesn't lose the rest of the
    batch. Returns (sent, failed) lists of email addresses."""
    sent = []
    failed = []
    connection = get_connection()
    connection.open()
    sent_since_reconnect = 0
    try:
        for email, subject, body in messages:
            if sent_since_reconnect >= EMAILS_PER_CONNECTION:
                connection.close()
                connection = get_connection()
                connection.open()
                sent_since_reconnect = 0
            try:
                send_mail(
                    subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False, connection=connection
                )
                sent.append(email)
                sent_since_reconnect += 1
            except Exception:
                logger.exception("Failed to send notification email to %s", email)
                failed.append(email)
                # the connection may be in a broken state after a failed send
                connection.close()
                connection = get_connection()
                connection.open()
                sent_since_reconnect = 0
    finally:
        connection.close()
    return sent, failed
