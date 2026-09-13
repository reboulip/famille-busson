"""Interactive first-run setup for a fresh install: site identity, first
superuser, default groups and starter document categories.

Usage (from the repo root):
    uv run python manage.py bootstrap_site
    uv run python manage.py bootstrap_site --noinput --site-name "..." \\
        --admin-first-name "..." --admin-last-name "..." \\
        --admin-email "..." --admin-password "..."

Idempotent: safe to re-run. Anything already created (an Account matching
--admin-email, or an existing SiteConfig row) is left untouched and reported
as skipped -- a re-run never overwrites an already-configured site.
"""

from __future__ import annotations

import getpass

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from annuaire.models import Account, Person, SiteConfig
from documents.models import Category

HELP_TEXT = __doc__ or ""

# Generic starting point, not this deployment's own vocabulary -- a fresh
# install's staff are expected to rename/extend these once real membership
# and document structure exist.
DEFAULT_GROUPS = ["Famille proche", "Famille élargie"]
STARTER_CATEGORIES = ["Général", "Administratif"]


class Command(BaseCommand):
    help = HELP_TEXT

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt; require every value via the flags below.",
        )
        parser.add_argument("--site-name", dest="site_name", default=None)
        parser.add_argument("--wordmark", dest="wordmark", default=None)
        parser.add_argument("--tagline", dest="tagline", default="")
        parser.add_argument("--sender-address", dest="sender_address", default="")
        parser.add_argument("--feedback-url", dest="feedback_url", default="")
        parser.add_argument("--admin-first-name", dest="admin_first_name", default=None)
        parser.add_argument("--admin-last-name", dest="admin_last_name", default=None)
        parser.add_argument("--admin-email", dest="admin_email", default=None)
        parser.add_argument("--admin-password", dest="admin_password", default=None)

    def handle(self, *args, **options):
        interactive = options["interactive"]

        if interactive:
            values = self._prompt_for_values()
        else:
            values = self._values_from_options(options)

        self._bootstrap_admin(values)
        self._bootstrap_groups()
        self._bootstrap_categories()
        self._bootstrap_site_config(values)

    # -- value collection ---------------------------------------------------

    def _values_from_options(self, options) -> dict:
        required = {
            "site_name": options["site_name"],
            "admin_first_name": options["admin_first_name"],
            "admin_last_name": options["admin_last_name"],
            "admin_email": options["admin_email"],
            "admin_password": options["admin_password"],
        }
        missing = [f"--{name.replace('_', '-')}" for name, value in required.items() if not value]
        if missing:
            raise CommandError("The following arguments are required when using --noinput: " + ", ".join(missing))
        return {
            **required,
            "wordmark": options["wordmark"] if options["wordmark"] is not None else options["site_name"],
            "tagline": options["tagline"],
            "sender_address": options["sender_address"],
            "feedback_url": options["feedback_url"],
        }

    def _prompt_for_values(self) -> dict:
        self.stdout.write("Bootstrapping a new site. Press Ctrl-C to abort at any time.\n")

        site_name = self._prompt_required("Site name")
        wordmark = input(f"Wordmark [{site_name}]: ").strip() or site_name
        tagline = input("Tagline (optional): ").strip()
        sender_address = input("Sender email address (optional): ").strip()
        feedback_url = input("Feedback/bug-report URL (optional): ").strip()

        self.stdout.write("\nFirst administrator account:")
        admin_first_name = self._prompt_required("First name")
        admin_last_name = self._prompt_required("Last name")
        admin_email = self._prompt_email()
        admin_password = self._prompt_password()

        return {
            "site_name": site_name,
            "wordmark": wordmark,
            "tagline": tagline,
            "sender_address": sender_address,
            "feedback_url": feedback_url,
            "admin_first_name": admin_first_name,
            "admin_last_name": admin_last_name,
            "admin_email": admin_email,
            "admin_password": admin_password,
        }

    def _prompt_required(self, label: str) -> str:
        while True:
            value = input(f"{label}: ").strip()
            if value:
                return value
            self.stderr.write(f"{label} cannot be blank.")

    def _prompt_email(self) -> str:
        while True:
            value = input("Admin email: ").strip()
            try:
                validate_email(value)
            except ValidationError:
                self.stderr.write("Enter a valid email address.")
                continue
            return value

    def _prompt_password(self) -> str:
        while True:
            password = getpass.getpass("Admin password: ")
            try:
                validate_password(password)
            except ValidationError as exc:
                for message in exc.messages:
                    self.stderr.write(message)
                continue
            confirm = getpass.getpass("Admin password (again): ")
            if password != confirm:
                self.stderr.write("Passwords didn't match.")
                continue
            return password

    # -- bootstrap steps ------------------------------------------------------

    def _bootstrap_admin(self, values: dict):
        if Account.objects.filter(email=values["admin_email"]).exists():
            self.stdout.write(f"  · admin {values['admin_email']} already exists, skipping")
            return
        # Person first, Account second: the Account post_save signal links an
        # accountless Person matching the same email automatically, so the
        # admin lands on a working profile instead of the signup redirect.
        Person.objects.create(
            first_name=values["admin_first_name"],
            last_name=values["admin_last_name"],
            email=values["admin_email"],
        )
        admin = Account.objects.create_superuser(
            email=values["admin_email"],
            password=values["admin_password"],
        )
        admin.must_change_password = False
        admin.save()
        self.stdout.write(f"  · created superuser {admin.email}")

    def _bootstrap_groups(self):
        for name in DEFAULT_GROUPS:
            _, created = Group.objects.get_or_create(name=name)
            self.stdout.write(f"  · {'created' if created else 'already exists'} group: {name}")

    def _bootstrap_categories(self):
        for name in STARTER_CATEGORIES:
            _, created = Category.objects.get_or_create(name=name)
            self.stdout.write(f"  · {'created' if created else 'already exists'} document category: {name}")

    def _bootstrap_site_config(self, values: dict):
        if SiteConfig.objects.exists():
            self.stdout.write("  · SiteConfig already configured, skipping")
            return
        SiteConfig.objects.create(
            site_name=values["site_name"],
            wordmark=values["wordmark"],
            tagline=values["tagline"],
            sender_address=values["sender_address"],
            feedback_url=values["feedback_url"],
        )
        self.stdout.write(f"  · created SiteConfig for {values['site_name']}")
