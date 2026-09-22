"""Message builders for the app's outgoing emails.

Kept out of the views/commands that trigger them so the same builder can be used by
the real sender and by `manage.py preview_emails`, and so the templates have exactly
one place that decides their context.

Rendering and transport live in `annuaire.email_utils`; this module only decides what
goes into each message.
"""

from __future__ import annotations

import logging
import unicodedata

from django.conf import settings
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from annuaire.email_utils import InlineImage, OutgoingEmail, absolute_url, email_context, render_email
from annuaire.models import Person

logger = logging.getLogger("django")

# Roughly two lines at the email's body size. Long enough to say what the post is
# about, short enough that it does not become a substitute for opening it.
POST_EXCERPT_LENGTH = 160

# A profile photo is content, not decoration (design/emails/SPEC.md), but it still
# travels in every copy of the message -- one per subscriber. Skip anything large
# enough to make a batch heavy, and fall back to the initials disc.
MAX_INLINE_PHOTO_BYTES = 400 * 1024


def initials(person) -> str:
    """Two letters for the fallback avatar disc, accents stripped so the glyphs are
    guaranteed to exist in the email-safe serif stack."""
    letters = f"{person.first_name[:1]}{person.last_name[:1]}".upper()
    return "".join(c for c in unicodedata.normalize("NFD", letters) if unicodedata.category(c) != "Mn")


def birthday_photo(person) -> InlineImage | None:
    """Read the person's profile photo for embedding, or None to use the initials disc.

    Best-effort: a missing file on disk (a row whose upload was cleaned up, a media
    volume not mounted) must degrade to the fallback, never break the whole batch.
    """
    photo = getattr(person, "profile_photo", None)
    if not photo:
        return None
    try:
        if photo.size > MAX_INLINE_PHOTO_BYTES:
            return None
        with photo.open("rb") as handle:
            data = handle.read()
    except (OSError, ValueError):
        logger.warning("Could not read profile photo for person %s; using initials instead", person.pk)
        return None
    return InlineImage(cid="profile-photo", data=data, filename=photo.name.rsplit("/", 1)[-1])


def _settings_url(recipient: Person | None) -> str:
    """The recipient's own profile-edit page, deep-linked to the notifications
    fieldset -- falls back to the generic redirect when the caller has no Person
    (e.g. a flow with no single recipient to link to)."""
    if recipient is not None:
        return absolute_url(reverse("person-edit", kwargs={"pk": recipient.pk})) + "#notifications"
    return absolute_url(reverse("edit-my-profile"))


def _recipient_language(recipient: Person | None) -> str:
    """The recipient's saved language preference, or the site default when
    they have none (never had an account, or never chose one)."""
    if recipient is not None and recipient.account_id and recipient.account.language:
        return recipient.account.language
    return settings.LANGUAGE_CODE


def birthday_reminder(
    person, recipient_email: str, photo: InlineImage | None, *, recipient: Person | None = None
) -> OutgoingEmail:
    with translation.override(_recipient_language(recipient)):
        context = email_context(
            person=person,
            initials=initials(person),
            photo_cid=photo.cid if photo else None,
            profile_url=absolute_url(reverse("personne-detail", kwargs={"pk": person.pk})),
            settings_url=_settings_url(recipient),
            cta_label=_("Voir le profil de %(first_name)s") % {"first_name": person.first_name},
        )
        html, text = render_email(
            "annuaire/emails/birthday_reminder.html",
            "annuaire/emails/birthday_reminder.txt",
            context,
        )
        return OutgoingEmail(
            to=recipient_email,
            # Subject unchanged from the plain-text era -- subscribers filter on it.
            subject=_("Anniversaire de %(first_name)s %(last_name)s")
            % {"first_name": person.first_name, "last_name": person.last_name},
            text_body=text,
            html_body=html,
            inline_images=(photo,) if photo else (),
        )


def new_blog_post(post, recipient_email: str, *, recipient: Person | None = None) -> OutgoingEmail:
    from annuaire.markdown_utils import markdown_to_text

    with translation.override(_recipient_language(recipient)):
        excerpt = " ".join((markdown_to_text(post.body) or "").split())
        if len(excerpt) > POST_EXCERPT_LENGTH:
            excerpt = excerpt[:POST_EXCERPT_LENGTH].rstrip() + "…"

        authors = ", ".join(str(author) for author in post.authors.all())
        context = email_context(
            post=post,
            authors=authors,
            excerpt=excerpt,
            post_url=absolute_url(reverse("blogpost-detail", kwargs={"pk": post.pk})),
            settings_url=_settings_url(recipient),
        )
        html, text = render_email(
            "publications/emails/new_blog_post.html",
            "publications/emails/new_blog_post.txt",
            context,
        )
        return OutgoingEmail(
            to=recipient_email,
            subject=_("Nouvel article : %(title)s") % {"title": post.title},
            text_body=text,
            html_body=html,
        )


def event_announcement(event, recipient_email: str, *, recipient: Person | None = None) -> OutgoingEmail:
    with translation.override(_recipient_language(recipient)):
        context = email_context(
            event=event,
            event_url=absolute_url(reverse("event-detail", kwargs={"pk": event.pk})),
            settings_url=_settings_url(recipient),
        )
        html, text = render_email(
            "events/emails/event_announcement.html",
            "events/emails/event_announcement.txt",
            context,
        )
        return OutgoingEmail(
            to=recipient_email,
            subject=_("Nouvel événement : %(title)s") % {"title": event.title},
            text_body=text,
            html_body=html,
        )


def event_reminder(event, recipient_email: str, *, recipient: Person | None = None) -> OutgoingEmail:
    with translation.override(_recipient_language(recipient)):
        context = email_context(
            event=event,
            event_url=absolute_url(reverse("event-detail", kwargs={"pk": event.pk})),
            settings_url=_settings_url(recipient),
        )
        html, text = render_email(
            "events/emails/event_reminder.html",
            "events/emails/event_reminder.txt",
            context,
        )
        return OutgoingEmail(
            to=recipient_email,
            subject=_("Rappel : %(title)s") % {"title": event.title},
            text_body=text,
            html_body=html,
        )


def account_setup(account_email: str, reset_url: str, is_reset: bool, *, language: str | None = None) -> OutgoingEmail:
    """No `recipient: Person` here (unlike the other builders): this fires from
    account creation/reset flows keyed on a bare email address, before any
    Person/Account link is guaranteed to exist yet. `language` lets a caller
    that does know a preference (e.g. an existing Account being reset) pass it
    explicitly; defaults to the site's active language otherwise."""
    with translation.override(language or settings.LANGUAGE_CODE):
        context = email_context(account_email=account_email, reset_url=reset_url, is_reset=is_reset)
        subject = (
            _("Votre mot de passe a été réinitialisé")
            if is_reset
            else _("Votre compte %(site_name)s") % {"site_name": context["site_name"]}
        )
        context["subject"] = subject
        html, text = render_email(
            "annuaire/emails/account_setup.html",
            "annuaire/emails/account_setup.txt",
            context,
        )
        return OutgoingEmail(to=account_email, subject=subject, text_body=text, html_body=html)
