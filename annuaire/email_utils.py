import logging
import mimetypes
from dataclasses import dataclass, field

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

logger = logging.getLogger("django")

# A fresh SMTP connection per email pushed large batches past the provider's timeout
# (see BulkAccountCreateView, annuaire/views.py). Reuse one connection across a batch,
# cycling it periodically so a long-lived connection doesn't itself get dropped.
EMAILS_PER_CONNECTION = 15


@dataclass(frozen=True)
class InlineImage:
    """An image embedded in the message body rather than linked from it.

    Linking is not an option for member photos: MEDIA_URL is served by
    `media_serve` behind `@login_required` on purpose (uploaded files must not be
    readable by anyone who obtains the URL), and an email client fetching an
    `<img src>` is not logged in -- it would follow the redirect and render the
    login page. Embedding sidesteps that without opening the media route up.

    Reference it from the HTML as `src="cid:{cid}"`.
    """

    cid: str
    data: bytes
    filename: str

    @property
    def mimetype(self) -> str:
        guessed, _ = mimetypes.guess_type(self.filename)
        return guessed if guessed and guessed.startswith("image/") else "application/octet-stream"


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text_body: str
    html_body: str | None = None
    inline_images: tuple[InlineImage, ...] = field(default_factory=tuple)

    @classmethod
    def coerce(cls, message) -> "OutgoingEmail":
        """Accept either an OutgoingEmail or a legacy `(email, subject, body)` tuple.

        The tuple form predates HTML emails and is still the shortest way to send a
        text-only message; it is not deprecated."""
        if isinstance(message, cls):
            return message
        to, subject, text_body = message
        return cls(to=to, subject=subject, text_body=text_body)


class _InlineImageEmail(EmailMultiAlternatives):
    """Nests inline images in a `multipart/related` wrapped around the HTML part.

    Django builds `multipart/mixed` for attachments, which makes an inline image
    show up as a loose file *and* leaves the `cid:` reference free not to resolve.
    The structure clients actually expect is::

        multipart/alternative
        |-- text/plain                 <- text-only clients stop here, see no image
        `-- multipart/related
            |-- text/html
            `-- image/...              <- Content-ID, disposition inline

    Django 6 has no API for that (`mixed_subtype` was removed and `make_mixed()` is
    hardcoded), so we let it build the alternative pair and then convert the HTML
    leaf in place with the stdlib's own `make_related()` / `add_related()`.
    """

    def __init__(self, *args, inline_images=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.inline_images = tuple(inline_images)

    def message(self, **kwargs):
        # Django 6 declares `message(self, *, policy=...)`; accept and forward whatever
        # it passes rather than pinning the signature here.
        mime = super().message(**kwargs)
        if not self.inline_images:
            return mime
        for part in mime.walk():
            if part.get_content_type() != "text/html":
                continue
            part.make_related()
            for image in self.inline_images:
                maintype, _, subtype = image.mimetype.partition("/")
                part.add_related(
                    image.data,
                    maintype=maintype,
                    subtype=subtype,
                    # The angle brackets are Content-ID syntax; the `cid:` URL in the
                    # HTML references the value *without* them.
                    cid=f"<{image.cid}>",
                    filename=image.filename,
                    disposition="inline",
                )
            break
        return mime


def build_message(email: OutgoingEmail, connection=None) -> EmailMultiAlternatives:
    message = _InlineImageEmail(
        subject=email.subject,
        body=email.text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email.to],
        connection=connection,
        inline_images=email.inline_images,
    )
    if email.html_body:
        message.attach_alternative(email.html_body, "text/html")
    return message


def send_bulk_emails(messages):
    """Send `OutgoingEmail`s (or legacy `(email, subject, body)` tuples) over a shared,
    periodically-cycled SMTP connection. Best-effort per recipient: one failure doesn't
    lose the rest of the batch. Returns (sent, failed) lists of email addresses."""
    sent = []
    failed = []
    connection = get_connection()
    connection.open()
    sent_since_reconnect = 0
    try:
        for raw in messages:
            email = OutgoingEmail.coerce(raw)
            if sent_since_reconnect >= EMAILS_PER_CONNECTION:
                connection.close()
                connection = get_connection()
                connection.open()
                sent_since_reconnect = 0
            try:
                build_message(email, connection=connection).send(fail_silently=False)
                sent.append(email.to)
                sent_since_reconnect += 1
            except Exception:
                logger.exception("Failed to send notification email to %s", email.to)
                failed.append(email.to)
                # the connection may be in a broken state after a failed send
                connection.close()
                connection = get_connection()
                connection.open()
                sent_since_reconnect = 0
    finally:
        connection.close()
    return sent, failed


def render_email(html_template: str, text_template: str, context: dict) -> tuple[str, str]:
    """Render the HTML and plain-text halves of one message.

    Every message ships both: some clients are configured to show text only, and a
    multipart message with no text part reads as a spam signal.
    """
    return render_to_string(html_template, context), render_to_string(text_template, context)


def email_context(**extra) -> dict:
    """Shared context for every email template: absolute URLs (an email has no
    request to resolve relative links against) and the site name."""
    context = {
        "site_base_url": settings.SITE_BASE_URL.rstrip("/"),
        "site_name": "Famille Busson",
    }
    context.update(extra)
    return context


def absolute_url(path: str) -> str:
    return settings.SITE_BASE_URL.rstrip("/") + path
