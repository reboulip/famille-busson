"""Render (and optionally send) any of the app's five emails without waiting for a
real trigger.

Email rendering is otherwise near-impossible to check: you would have to wait for a
real birthday, publish a real post, or reset a real password, and even then the result
only exists in someone's inbox. This renders each flow against real rows from the
database (or a throwaway stub when the table is empty) so the HTML can be opened in a
browser, and can send the message to a real address to see what an actual client makes
of it.

Usage (from the repo root):

    # write every flow to /tmp/email-preview/ and print the paths
    uv run python manage.py preview_emails

    # one flow only
    uv run python manage.py preview_emails --flow birthday

    # send it somewhere real (uses the configured EMAIL_BACKEND)
    uv run python manage.py preview_emails --flow magic-link --to moi@example.com

Note the two PasswordResetView-based flows (password reset, magic link) are rendered
here with a *fake* uid/token: they are previews, and their links will not authenticate.
Everything else about them -- layout, copy, colours -- is exactly what a real send
produces.
"""

from __future__ import annotations

import pathlib

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string

from annuaire import emails
from annuaire.email_utils import OutgoingEmail, absolute_url, build_message, email_context
from annuaire.models import Person

FLOWS = ("birthday", "new-post", "account-setup", "password-reset", "magic-link")

DEFAULT_OUT_DIR = "/tmp/email-preview"


class _StubPerson:
    """Stand-in when the database has no rows to preview against."""

    pk = 1
    first_name = "Camille"
    last_name = "Busson"
    profile_photo = None


class _StubPost:
    pk = 1
    title = "Rénovation du chalet du Lac"
    body = (
        "Les travaux de la toiture commencent lundi. On a retenu le devis de l'entreprise "
        "de Praz-sur-Verre, qui refait aussi la fascia et les rives. Prévoir du bruit les "
        "deux premières semaines, mais après on devrait être tranquilles pour vingt ans."
    )

    class _Authors:
        @staticmethod
        def all():
            return ["Julien Simon", "Margaux Simon"]

    authors = _Authors()


class Command(BaseCommand):
    help = __doc__ or ""

    def add_arguments(self, parser):
        parser.add_argument("--flow", choices=FLOWS, help="Render only this flow (default: all).")
        parser.add_argument("--to", help="Send the rendered email to this address instead of writing a file.")
        parser.add_argument(
            "--out-dir", default=DEFAULT_OUT_DIR, help=f"Where to write HTML (default {DEFAULT_OUT_DIR})."
        )

    def handle(self, *args, **options):
        flows = [options["flow"]] if options["flow"] else list(FLOWS)
        recipient = options["to"] or "preview@example.com"

        out_dir = pathlib.Path(options["out_dir"])
        if not options["to"]:
            out_dir.mkdir(parents=True, exist_ok=True)

        for flow in flows:
            message = self._build(flow, recipient)
            if options["to"]:
                build_message(message).send(fail_silently=False)
                self.stdout.write(self.style.SUCCESS(f"{flow}: envoyé à {recipient} — « {message.subject} »"))
            else:
                path = out_dir / f"{flow}.html"
                path.write_text(message.html_body or "", encoding="utf-8")
                text_path = out_dir / f"{flow}.txt"
                text_path.write_text(message.text_body, encoding="utf-8")
                self.stdout.write(f"{flow}: {path}  (texte : {text_path})")

        if not options["to"]:
            self.stdout.write("")
            self.stdout.write("Ouvrez les .html dans un navigateur. Pour un vrai client : --to <adresse>.")

    def _build(self, flow: str, recipient: str) -> OutgoingEmail:
        if flow == "birthday":
            person = Person.objects.exclude(deceased=True).order_by("pk").first() or _StubPerson()
            photo = emails.birthday_photo(person)
            # _StubPerson isn't a real Person -- only pass it as the deep-link recipient
            # when the database actually produced one.
            settings_recipient = person if isinstance(person, Person) else None
            return emails.birthday_reminder(person, recipient, photo, recipient=settings_recipient)

        if flow == "new-post":
            from publications.models import BlogPost

            post = BlogPost.objects.prefetch_related("authors").order_by("-pk").first() or _StubPost()
            return emails.new_blog_post(post, recipient)

        if flow == "account-setup":
            return emails.account_setup(recipient, absolute_url("/annuaire/password/reset/apercu/"), is_reset=False)

        # The two PasswordResetView flows render through Django's own machinery, so
        # rebuild the context it would pass rather than going through emails.py.
        if flow in ("password-reset", "magic-link"):
            return self._build_reset_like(flow, recipient)

        raise CommandError(f"Unknown flow {flow!r}")

    def _build_reset_like(self, flow: str, recipient: str) -> OutgoingEmail:
        base = absolute_url("")
        protocol, _, domain = base.partition("://")
        context = email_context(
            email=recipient,
            uid="APERCU",
            token="apercu-token",
            protocol=protocol or "http",
            domain=domain or "localhost:8000",
            validity_minutes=15,
        )
        if flow == "password-reset":
            html_template, text_template = "annuaire/emails/password_reset.html", "annuaire/password_reset_email.txt"
            subject = "Réinitialiser votre mot de passe"
        else:
            html_template, text_template = "annuaire/emails/magic_link.html", "annuaire/magic_link_email.txt"
            subject = "Votre lien de connexion"
        return OutgoingEmail(
            to=recipient,
            subject=subject,
            text_body=render_to_string(text_template, context),
            html_body=render_to_string(html_template, context),
        )
