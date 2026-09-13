import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, Permission, PermissionsMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


def _language_choices():
    # A named module-level function, not a lambda: migration serialization
    # can't pickle a lambda, but can reference an importable function -- and
    # calling it at field-access time (not at class-definition time) means the
    # choice list stays live even after Phase 15.4 replaces settings.LANGUAGES.
    return settings.LANGUAGES


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("L'adresse email est obligatoire"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name=_("Adresse email"))
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))
    is_staff = models.BooleanField(default=False, verbose_name=_("Membre du personnel"))
    must_change_password = models.BooleanField(default=False, verbose_name=_("Doit changer le mot de passe"))
    groups = models.ManyToManyField(Group, related_name="account_set", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="account_set", blank=True)
    # Not last_login: Django's own update_last_login receiver overwrites that on
    # every login, which would make a "since last visit" feed empty for anyone
    # who just logged in. Stamped at the END of each activity feed GET instead.
    last_feed_seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Dernière consultation du fil"))
    # Per-account tokenised .ics feed (12.5) -- unique so a lookup by token
    # resolves exactly one account. Lazily generated, never on a form.
    calendar_token = models.CharField(
        max_length=64, unique=True, null=True, blank=True, editable=False, verbose_name=_("Jeton calendrier")
    )
    # Consent tracking for the privacy notice (14.3) -- see annuaire/privacy_notice.py.
    # Not on Person: acceptance is an act of the logged-in human, and an
    # accountless Person (a child, a deceased ancestor) can't consent.
    privacy_notice_accepted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Date d'acceptation de la politique de confidentialité")
    )
    privacy_notice_version = models.CharField(
        max_length=20, blank=True, default="", verbose_name=_("Version acceptée de la politique de confidentialité")
    )
    # Per-account UI language preference (Phase 15.5) -- on Account, not
    # Person/Settings: choosing a display language is an act of the logged-in
    # human, and Person.owners co-editability would otherwise let another
    # member change it (same rationale as privacy_notice_accepted_at above).
    # Blank means "no preference yet" -- resolve_language() falls through to
    # the cookie/site-default/browser/settings chain (see annuaire/i18n.py).
    language = models.CharField(
        max_length=10, blank=True, default="", choices=_language_choices, verbose_name=_("Langue")
    )
    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def get_or_create_calendar_token(self) -> str:
        token = self.calendar_token
        if not token:
            token = secrets.token_urlsafe(32)
            self.calendar_token = token
            self.save(update_fields=["calendar_token"])
        return str(token)

    def regenerate_calendar_token(self) -> str:
        self.calendar_token = secrets.token_urlsafe(32)
        self.save(update_fields=["calendar_token"])
        return self.calendar_token


class Person(models.Model):
    class ExportPrivacy(models.TextChoices):
        AUTO = "auto", _("Automatique (masqué·e tant que vivant·e)")
        SHARE = "share", _("Toujours partager")
        REDACT = "redact", _("Toujours masquer")

    # pgettext_lazy: "Nom" here means a person's surname, a different sense than
    # Chalet.name ("Nom" as in the chalet's own name/label).
    last_name = models.CharField(max_length=100, verbose_name=pgettext_lazy("person", "Nom"))
    account = models.OneToOneField(
        Account, related_name="profile", on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Compte")
    )
    first_name = models.CharField(max_length=100, verbose_name=_("Prénom"))
    email = models.EmailField(blank=True, null=True, verbose_name=_("Adresse électronique"))
    profile_photo = models.ImageField(upload_to="photos/", blank=True, null=True, verbose_name=_("Photo de profil"))
    postal_address = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Adresse postale"))
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Latitude"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Longitude"))
    phone_number = models.CharField(max_length=25, blank=True, null=True, verbose_name=_("Numéro de téléphone"))
    birth_date = models.DateField(blank=True, null=True, verbose_name=_("Date de naissance"))
    # Free text, not geocoded: historical place names rarely resolve in a modern
    # geocoder, and a lat/long here would put deceased ancestors on the carte.
    # Collected for genealogical record-keeping (tree display, future GEDCOM
    # export) -- see ProfileEditForm's help_text.
    birth_place = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu de naissance"))
    # Staff/superuser-only (see ProfileEditForm, which pops both fields for anyone
    # else). Unlike `gender` -- added then deliberately removed in migration 0007,
    # with two standing regression guards against its return -- this field's
    # technical necessity is concrete: it drives real behaviour (suppressing
    # birthday reminders, excluding from the "sans adresse géolocalisée" count) and,
    # by explicit product decision, a visible "date de décès" line on the profile
    # page. Treat that visible line as a deliberate, narrow exception -- not a
    # precedent for surfacing more personal-status text elsewhere without asking.
    deceased = models.BooleanField(default=False, verbose_name=_("Décédé·e"))
    death_date = models.DateField(blank=True, null=True, verbose_name=_("Date de décès"))
    death_place = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu de décès"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Infos utiles"))
    # Governs redaction in the GEDCOM export by default (auto = redacted while
    # living); the Excel export and iCal feed are otherwise unaffected by this
    # setting except for the explicit "redact" state, which they also honour --
    # see annuaire/privacy.py, the single source of truth every export surface
    # calls instead of re-deriving "is this person alive" itself.
    export_privacy = models.CharField(
        max_length=6,
        choices=ExportPrivacy.choices,
        default=ExportPrivacy.AUTO,
        blank=True,
        verbose_name=_("Confidentialité dans les exports"),
    )
    owners = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="managed_profiles",
        blank=True,
        verbose_name=_("Propriétaires"),
    )
    # Erasure (14.2, annuaire/anonymisation.py) -- set once, never cleared: an
    # anonymisation is a one-way door, unlike a soft delete.
    anonymised_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Anonymisé·e le"))
    search_vector = SearchVectorField(null=True, editable=False, verbose_name=_("Vecteur de recherche"))
    search_text = models.TextField(blank=True, default="", editable=False, verbose_name=_("Texte de recherche"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Settings(models.Model):
    person = models.OneToOneField(Person, related_name="settings", on_delete=models.CASCADE, verbose_name=_("Profil"))
    notify_on_birthday = models.BooleanField(
        default=True, blank=True, verbose_name=_("Recevoir un rappel pour les anniversaires")
    )
    notify_on_new_blog_post = models.BooleanField(
        default=True, blank=True, verbose_name=_("Recevoir une notification pour les nouveaux articles")
    )
    # Covers both the creation announcement and the pre-event reminder -- one
    # preference, not two (see events.signals/events.tasks).
    notify_on_event = models.BooleanField(
        default=True, blank=True, verbose_name=_("Recevoir les annonces et rappels d'événements")
    )

    class Meta:
        verbose_name = _("Paramètres de notification")
        verbose_name_plural = _("Paramètres de notification")

    def __str__(self):
        return f"Paramètres de {self.person}"


class Relation(models.Model):
    RELATION_CHOICES = [
        (0, _("mariage")),
        (1, _("conjoint")),
        (2, _("parent")),
        (3, _("enfant")),
    ]

    person1 = models.ForeignKey(
        "Person", related_name="ascending_relations", on_delete=models.CASCADE, verbose_name=_("Personne")
    )
    person2 = models.ForeignKey(
        "Person", related_name="descending_relations", on_delete=models.CASCADE, verbose_name=_("En relation avec")
    )
    relationship_type = models.IntegerField(choices=RELATION_CHOICES, verbose_name=_("Type de relation"))
    # For a mariage/conjoint row, start_date IS the marriage date -- there is no
    # separate marriage_date field, to avoid two sources of truth for the same
    # fact. marriage_place/end_date are spouse-only too; both are mirrored onto
    # the inverse row by create_inverse_relation and nulled/blanked there for
    # parent/child rows -- see annuaire/signals.py.
    start_date = models.DateField(blank=True, null=True, verbose_name=_("Date de début"))
    marriage_place = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu du mariage"))
    end_date = models.DateField(blank=True, null=True, verbose_name=_("Date de fin"))

    def __str__(self):
        return f"{self.person1} -> {self.get_relationship_type_display()} -> {self.person2}"


class Chalet(models.Model):
    # pgettext_lazy: "Nom" here means the chalet's own name/label, a different
    # sense than Person.last_name ("Nom" as in surname).
    name = models.CharField(max_length=100, verbose_name=pgettext_lazy("chalet", "Nom"))
    address = models.CharField(max_length=255, verbose_name=_("Adresse"))
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Latitude"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Longitude"))
    photo = models.ImageField(upload_to="photos/", blank=True, null=True, verbose_name=_("Photo"))
    owners = models.ManyToManyField(
        "Person", related_name="owned_chalets", blank=True, verbose_name=_("Propriétaires")
    )

    def __str__(self):
        return self.name


class PresencePSV(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, verbose_name=_("Personne"))
    chalet = models.ForeignKey(Chalet, on_delete=models.CASCADE, verbose_name=_("Chalet"))
    start_date = models.DateField(verbose_name=_("Date d'arrivée"))
    end_date = models.DateField(verbose_name=_("Date de départ"))

    def __str__(self):
        return f"{self.person} - {self.chalet} du {self.start_date} au {self.end_date}"


class AuditEvent(models.Model):
    """One row per tracked change -- see annuaire/audit.py for how these get
    created. content_type/object_id/object_repr (not a GenericForeignKey) so a
    row about a since-deleted/purged object still renders. actor points at
    Account (never Person -- would trip test_person_meta_guard_covers_every_relation
    in annuaire/person_merge.py), with a denormalized label so the row survives
    account deletion/anonymisation."""

    class Action(models.TextChoices):
        CREATE = "create", _("Création")
        UPDATE = "update", _("Modification")
        DELETE = "delete", _("Suppression")
        RESTORE = "restore", _("Restauration")
        PURGE = "purge", _("Purge définitive")
        MEMBERSHIP_ADD = "membership_add", _("Ajout à un groupe")
        MEMBERSHIP_REMOVE = "membership_remove", _("Retrait d'un groupe")
        ANONYMISE = "anonymise", _("Anonymisation")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("Type d'objet"))
    object_id = models.CharField(max_length=64, verbose_name=_("Identifiant de l'objet"))
    object_repr = models.CharField(max_length=200, verbose_name=_("Objet"))
    action = models.CharField(max_length=20, choices=Action.choices, verbose_name=_("Action"))
    # {"field": {"from": "...", "to": "..."}}, values always coerced to strings --
    # never password/calendar_token/search_vector/search_text, see audit.py.
    changes = models.JSONField(default=dict, blank=True, verbose_name=_("Modifications"))
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Auteur"),
    )
    actor_label = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Auteur (archivé)"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = _("Événement d'audit")
        verbose_name_plural = _("Événements d'audit")

    def __str__(self):
        return f"{self.get_action_display()} — {self.object_repr}"


class SiteConfig(models.Model):
    """Singleton holding the site's identity and configuration (Phase 15) --
    pinned to pk=1 so there is always at most one row. Never construct this
    directly in a read path; use annuaire.site_config.get_site_config(),
    which never creates a row (only SiteConfigUpdateView/bootstrap_site do)."""

    site_name = models.CharField(max_length=100, blank=True, default="", verbose_name=_("Nom du site"))
    # Separate from site_name, not derived from it -- the wordmark can carry
    # its own typographic treatment (e.g. a non-breaking space between words).
    wordmark = models.CharField(max_length=100, blank=True, default="", verbose_name=_("Wordmark"))
    tagline = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Accroche"))
    sender_address = models.EmailField(blank=True, default="", verbose_name=_("Adresse d'expédition des emails"))
    feedback_url = models.URLField(
        blank=True,
        default="",
        verbose_name=_("Lien de retour/signalement"),
        help_text=_("Laisser vide pour masquer le lien « Signaler un bug » du menu."),
    )
    timezone = models.CharField(max_length=64, default=settings.TIME_ZONE, verbose_name=_("Fuseau horaire"))
    # Stored but inert until Phase 15.4's i18n scaffolding reads it -- no
    # language switching happens from this field alone yet.
    default_language = models.CharField(
        max_length=10,
        blank=True,
        default="",
        choices=_language_choices,
        verbose_name=_("Langue par défaut"),
        help_text=_("Sans effet tant que l'internationalisation (phase 15.4) n'est pas en place."),
    )
    # Names the entry in annuaire.theming.THEMES -- a real (if single-entry today)
    # registry/seam, not a hardcoded palette. Adding a second theme later means
    # adding a THEMES entry and a choice here, nothing else.
    theme = models.CharField(
        max_length=20, choices=[("alpenglow", "Alpenglow")], default="alpenglow", verbose_name=_("Thème")
    )
    # Blank means "use the theme's own default for this role" -- never stored as
    # a specific hex just because it happens to match the default. Validated in
    # FormSiteConfig.clean() against annuaire.contrast's AA thresholds, not here:
    # the model has no request-independent way to know which theme it's being
    # validated against once more than one theme exists.
    brand_primary_light = models.CharField(
        max_length=7, blank=True, default="", verbose_name=_("Couleur principale (clair)")
    )
    brand_primary_dark = models.CharField(
        max_length=7, blank=True, default="", verbose_name=_("Couleur principale (sombre)")
    )
    brand_accent_light = models.CharField(
        max_length=7, blank=True, default="", verbose_name=_("Couleur d'accent (clair)")
    )
    brand_accent_dark = models.CharField(
        max_length=7, blank=True, default="", verbose_name=_("Couleur d'accent (sombre)")
    )
    logo = models.ImageField(upload_to="branding/", blank=True, null=True, verbose_name=_("Logo"))
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True, verbose_name=_("Favicon"))
    # Cache-busting query string for the public branding-asset URLs -- a browser
    # or CDN must not keep serving last month's logo after staff replace it.
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Dernière modification"))

    class Meta:
        verbose_name = _("Configuration du site")
        verbose_name_plural = _("Configuration du site")

    def __str__(self):
        return self.site_name or str(_("Configuration du site"))

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(_("SiteConfig est un singleton : suppression interdite."))
