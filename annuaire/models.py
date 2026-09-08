import secrets

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, Permission, PermissionsMixin
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
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
    email = models.EmailField(unique=True, verbose_name="Adresse email")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_staff = models.BooleanField(default=False, verbose_name="Membre du personnel")
    must_change_password = models.BooleanField(default=False, verbose_name="Doit changer le mot de passe")
    groups = models.ManyToManyField(Group, related_name="account_set", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="account_set", blank=True)
    # Not last_login: Django's own update_last_login receiver overwrites that on
    # every login, which would make a "since last visit" feed empty for anyone
    # who just logged in. Stamped at the END of each activity feed GET instead.
    last_feed_seen_at = models.DateTimeField(null=True, blank=True, verbose_name="Dernière consultation du fil")
    # Per-account tokenised .ics feed (12.5) -- unique so a lookup by token
    # resolves exactly one account. Lazily generated, never on a form.
    calendar_token = models.CharField(
        max_length=64, unique=True, null=True, blank=True, editable=False, verbose_name="Jeton calendrier"
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
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    account = models.OneToOneField(
        Account, related_name="profile", on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Compte"
    )
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    email = models.EmailField(blank=True, null=True, verbose_name="Adresse électronique")
    profile_photo = models.ImageField(upload_to="photos/", blank=True, null=True, verbose_name="Photo de profil")
    postal_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresse postale")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Longitude")
    phone_number = models.CharField(max_length=25, blank=True, null=True, verbose_name="Numéro de téléphone")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    # Free text, not geocoded: historical place names rarely resolve in a modern
    # geocoder, and a lat/long here would put deceased ancestors on the carte.
    # Collected for genealogical record-keeping (tree display, future GEDCOM
    # export) -- see ProfileEditForm's help_text.
    birth_place = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu de naissance")
    # Staff/superuser-only (see ProfileEditForm, which pops both fields for anyone
    # else). Unlike `gender` -- added then deliberately removed in migration 0007,
    # with two standing regression guards against its return -- this field's
    # technical necessity is concrete: it drives real behaviour (suppressing
    # birthday reminders, excluding from the "sans adresse géolocalisée" count) and,
    # by explicit product decision, a visible "date de décès" line on the profile
    # page. Treat that visible line as a deliberate, narrow exception -- not a
    # precedent for surfacing more personal-status text elsewhere without asking.
    deceased = models.BooleanField(default=False, verbose_name="Décédé·e")
    death_date = models.DateField(blank=True, null=True, verbose_name="Date de décès")
    death_place = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu de décès")
    description = models.TextField(blank=True, null=True, verbose_name="Infos utiles")
    owners = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="managed_profiles",
        blank=True,
        verbose_name="Propriétaires",
    )
    search_vector = SearchVectorField(null=True, editable=False, verbose_name="Vecteur de recherche")
    search_text = models.TextField(blank=True, default="", editable=False, verbose_name="Texte de recherche")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Settings(models.Model):
    person = models.OneToOneField(Person, related_name="settings", on_delete=models.CASCADE, verbose_name="Profil")
    notify_on_birthday = models.BooleanField(
        default=True, blank=True, verbose_name="Recevoir un rappel pour les anniversaires"
    )
    notify_on_new_blog_post = models.BooleanField(
        default=True, blank=True, verbose_name="Recevoir une notification pour les nouveaux articles"
    )
    # Covers both the creation announcement and the pre-event reminder -- one
    # preference, not two (see events.signals/events.tasks).
    notify_on_event = models.BooleanField(
        default=True, blank=True, verbose_name="Recevoir les annonces et rappels d'événements"
    )

    class Meta:
        verbose_name = "Paramètres de notification"
        verbose_name_plural = "Paramètres de notification"

    def __str__(self):
        return f"Paramètres de {self.person}"


class Relation(models.Model):
    RELATION_CHOICES = [
        (0, "mariage"),
        (1, "conjoint"),
        (2, "parent"),
        (3, "enfant"),
    ]

    person1 = models.ForeignKey(
        "Person", related_name="ascending_relations", on_delete=models.CASCADE, verbose_name="Personne"
    )
    person2 = models.ForeignKey(
        "Person", related_name="descending_relations", on_delete=models.CASCADE, verbose_name="En relation avec"
    )
    relationship_type = models.IntegerField(choices=RELATION_CHOICES, verbose_name="Type de relation")
    # For a mariage/conjoint row, start_date IS the marriage date -- there is no
    # separate marriage_date field, to avoid two sources of truth for the same
    # fact. marriage_place/end_date are spouse-only too; both are mirrored onto
    # the inverse row by create_inverse_relation and nulled/blanked there for
    # parent/child rows -- see annuaire/signals.py.
    start_date = models.DateField(blank=True, null=True, verbose_name="Date de début")
    marriage_place = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu du mariage")
    end_date = models.DateField(blank=True, null=True, verbose_name="Date de fin")

    def __str__(self):
        return f"{self.person1} -> {self.get_relationship_type_display()} -> {self.person2}"


class Chalet(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    address = models.CharField(max_length=255, verbose_name="Adresse")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Longitude")
    photo = models.ImageField(upload_to="photos/", blank=True, null=True, verbose_name="Photo")
    owners = models.ManyToManyField("Person", related_name="owned_chalets", blank=True, verbose_name="Propriétaires")

    def __str__(self):
        return self.name


class PresencePSV(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, verbose_name="Personne")
    chalet = models.ForeignKey(Chalet, on_delete=models.CASCADE, verbose_name="Chalet")
    start_date = models.DateField(verbose_name="Date d'arrivée")
    end_date = models.DateField(verbose_name="Date de départ")

    def __str__(self):
        return f"{self.person} - {self.chalet} du {self.start_date} au {self.end_date}"
