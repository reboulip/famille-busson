"""Phase 5.2 — the HTML email system.

The bar these tests hold: every message ships both halves (a client set to text-only
must still get something readable), the birthday photo travels *inside* the message
rather than as a link, and nothing about who receives what has changed.
"""

import io

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile

from annuaire import emails
from annuaire.email_utils import InlineImage, OutgoingEmail, build_message, send_bulk_emails
from annuaire.models import Person


def _png_bytes(size: int = 64) -> bytes:
    """A real (tiny) PNG, padded to `size` bytes so size limits can be exercised."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (217, 121, 63)).save(buf, format="PNG")
    data = buf.getvalue()
    return data + b"\0" * max(0, size - len(data))


@pytest.fixture
def person(db):
    return Person.objects.create(first_name="Émile", last_name="Lefevre", email="emile@example.com")


# ---------------------------------------------------------------------------
# Birthday reminder
# ---------------------------------------------------------------------------


def test_birthday_reminder_ships_both_halves(person):
    message = emails.birthday_reminder(person, "dest@example.com", photo=None)
    assert message.subject == "Anniversaire de Émile Lefevre"
    assert message.html_body and "<html" in message.html_body
    assert message.text_body and "<html" not in message.text_body
    # The plain-text half must still carry the link -- it is the whole point of the mail.
    assert f"/annuaire/personne/{person.pk}/" in message.text_body


def test_birthday_subject_is_unchanged_from_the_plain_text_era(person):
    # Subscribers may filter on it; the design pass was a rendering swap, not a rename.
    message = emails.birthday_reminder(person, "dest@example.com", photo=None)
    assert message.subject == f"Anniversaire de {person.first_name} {person.last_name}"


def test_birthday_without_a_photo_falls_back_to_initials(person):
    message = emails.birthday_reminder(person, "dest@example.com", photo=None)
    assert message.inline_images == ()
    assert "cid:" not in message.html_body
    # Accents stripped so the glyph is guaranteed to exist in the email-safe serif.
    assert ">EL<" in message.html_body.replace("\n", "").replace(" ", "")


def test_birthday_photo_is_embedded_not_linked(person):
    photo = InlineImage(cid="profile-photo", data=_png_bytes(), filename="emile.png")
    message = emails.birthday_reminder(person, "dest@example.com", photo=photo)

    assert 'src="cid:profile-photo"' in message.html_body
    # A linked media URL would be useless: MEDIA_URL is behind @login_required and an
    # email client cannot authenticate.
    assert "/media/" not in message.html_body

    mime = build_message(message).message()
    # The image must sit in a multipart/related *inside* the alternative, so a
    # text-only client stops at text/plain and never sees a loose attachment.
    assert mime.get_content_type() == "multipart/alternative"
    assert [p.get_content_type() for p in mime.walk()] == [
        "multipart/alternative",
        "text/plain",
        "multipart/related",
        "text/html",
        "image/png",
    ]
    images = [p for p in mime.walk() if p.get_content_type().startswith("image/")]
    assert images[0]["Content-ID"] == "<profile-photo>"
    assert images[0].get("Content-Disposition", "").startswith("inline")


def test_birthday_photo_reader_returns_none_without_a_photo(person):
    assert emails.birthday_photo(person) is None


def test_birthday_photo_reader_embeds_a_real_photo(person):
    person.profile_photo = SimpleUploadedFile("p.png", _png_bytes(), content_type="image/png")
    person.save()
    photo = emails.birthday_photo(person)
    assert photo is not None
    assert photo.cid == "profile-photo"
    assert photo.data.startswith(b"\x89PNG")


def test_birthday_photo_reader_skips_an_oversized_photo(person, monkeypatch):
    # The photo travels in every copy of the message, one per subscriber.
    monkeypatch.setattr(emails, "MAX_INLINE_PHOTO_BYTES", 32)
    person.profile_photo = SimpleUploadedFile("p.png", _png_bytes(4096), content_type="image/png")
    person.save()
    assert emails.birthday_photo(person) is None


def test_birthday_reminder_settings_link_falls_back_without_a_recipient(person):
    message = emails.birthday_reminder(person, "dest@example.com", photo=None)
    assert "/annuaire/profile/edit" in message.html_body


def test_birthday_reminder_settings_link_targets_the_recipient_directly(person, other_person):
    message = emails.birthday_reminder(person, "dest@example.com", photo=None, recipient=other_person)
    assert f"/annuaire/personne/{other_person.pk}/update#notifications" in message.html_body
    assert "/annuaire/profile/edit" not in message.html_body


def test_birthday_photo_reader_degrades_when_the_file_is_missing(person):
    """A row whose upload was cleaned up, or a media volume that isn't mounted, must
    fall back to initials rather than break the whole batch."""
    person.profile_photo = SimpleUploadedFile("p.png", _png_bytes(), content_type="image/png")
    person.save()
    person.profile_photo.storage.delete(person.profile_photo.name)
    assert emails.birthday_photo(person) is None


# ---------------------------------------------------------------------------
# New blog post
# ---------------------------------------------------------------------------


@pytest.fixture
def post(db):
    from publications.models import BlogPost

    return BlogPost.objects.create(title="Rénovation du chalet", body="# Titre\n\nLes travaux **commencent** lundi.")


def test_new_post_email_includes_a_stripped_excerpt(post):
    message = emails.new_blog_post(post, "dest@example.com")
    assert "Les travaux commencent lundi." in message.html_body
    # Markdown syntax must not leak into either half.
    assert "**" not in message.html_body
    assert "# Titre" not in message.text_body


def test_new_post_excerpt_is_truncated(db):
    from publications.models import BlogPost

    long_post = BlogPost.objects.create(title="Long", body="mot " * 500)
    message = emails.new_blog_post(long_post, "dest@example.com")
    assert "…" in message.text_body
    # The excerpt itself is capped; the surrounding template copy is not counted.
    excerpt_line = next(line for line in message.text_body.splitlines() if line.startswith("mot"))
    assert len(excerpt_line) <= emails.POST_EXCERPT_LENGTH + 1


def test_new_post_email_survives_an_empty_body(db):
    from publications.models import BlogPost

    empty = BlogPost.objects.create(title="Sans texte", body="")
    message = emails.new_blog_post(empty, "dest@example.com")
    assert message.subject == "Nouvel article : Sans texte"
    assert message.html_body


def test_new_post_subject_is_unchanged(post):
    assert emails.new_blog_post(post, "d@example.com").subject == f"Nouvel article : {post.title}"


def test_new_post_settings_link_targets_the_recipient_directly(post, person):
    message = emails.new_blog_post(post, "d@example.com", recipient=person)
    assert f"/annuaire/personne/{person.pk}/update#notifications" in message.html_body
    assert "/annuaire/profile/edit" not in message.html_body


# ---------------------------------------------------------------------------
# Account setup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("is_reset", "expected_subject"),
    [(False, "Votre compte Famille Busson"), (True, "Votre mot de passe a été réinitialisé")],
)
def test_account_setup_subject_and_copy(db, is_reset, expected_subject):
    message = emails.account_setup("nouveau@example.com", "https://example.com/reset/", is_reset=is_reset)
    assert message.subject == expected_subject
    assert "https://example.com/reset/" in message.text_body
    assert "https://example.com/reset/" in message.html_body
    assert "nouveau@example.com" in message.text_body


def test_account_setup_uses_the_restrained_treatment(db):
    """Credential mail gets the flat horizon, not the peaks -- understated reads as
    more trustworthy, and heavy styling weighs against spam filters."""
    message = emails.account_setup("a@example.com", "https://example.com/r/", is_reset=False)
    # Assert on the markup, not the class name: every message carries the same dark-mode
    # <style> block, so `em-snowcap` appears as a rule even where no peak is drawn. The
    # tall near-peak's inline border is what only the full treatment emits.
    assert "border-bottom:74px solid #4B5D3F" not in message.html_body
    assert 'class="em-horizon"' in message.html_body


def test_notification_emails_use_the_full_treatment(person):
    message = emails.birthday_reminder(person, "d@example.com", photo=None)
    assert "border-bottom:74px solid #4B5D3F" in message.html_body
    assert 'class="em-horizon"' not in message.html_body


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_send_bulk_emails_attaches_the_html_alternative():
    message = OutgoingEmail(to="d@example.com", subject="S", text_body="texte", html_body="<p>html</p>")
    sent, failed = send_bulk_emails([message])
    assert (sent, failed) == (["d@example.com"], [])
    assert mail.outbox[0].body == "texte"
    assert mail.outbox[0].alternatives[0][0] == "<p>html</p>"


@pytest.mark.django_db
def test_send_bulk_emails_still_accepts_legacy_tuples():
    """The 3-tuple form predates HTML email and is still the shortest way to send a
    text-only message."""
    sent, _ = send_bulk_emails([("d@example.com", "Sujet", "Contenu")])
    assert sent == ["d@example.com"]
    assert mail.outbox[0].body == "Contenu"
    assert not mail.outbox[0].alternatives


@pytest.mark.django_db
def test_every_flow_ships_a_plain_text_part(person, post):
    """A multipart message with no text part is both unreadable in text-only clients
    and a spam signal."""
    built = [
        emails.birthday_reminder(person, "d@example.com", photo=None),
        emails.new_blog_post(post, "d@example.com"),
        emails.account_setup("d@example.com", "https://example.com/r/", is_reset=False),
    ]
    for message in built:
        assert message.text_body.strip()
        assert message.html_body.strip()
