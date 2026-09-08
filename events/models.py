from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone

from annuaire.models import Person


class EventQuerySet(models.QuerySet):
    def upcoming(self, moment):
        """Events not yet finished as of `moment` -- Coalesce("end", "start") so an
        event with no `end` (shouldn't happen post-save(), see Event.save(), but
        kept defensive) can't silently vanish from every listing."""
        return self.annotate(_effective_end=Coalesce("end", "start")).filter(_effective_end__gte=moment)

    def past(self, moment):
        return self.annotate(_effective_end=Coalesce("end", "start")).filter(_effective_end__lt=moment)

    def overlapping(self, start, end):
        return self.annotate(_effective_end=Coalesce("end", "start")).filter(start__lte=end, _effective_end__gte=start)


class EventManager(models.Manager):
    """Plain Manager subclass wrapping EventQuerySet -- not QuerySet.as_manager(),
    which `ty` misreads as a missing-argument error on its classmethod (no
    existing usage of that idiom elsewhere in this codebase; PhotoManager is the
    established pattern for a custom queryset)."""

    def get_queryset(self):
        return EventQuerySet(self.model, using=self._db)

    def upcoming(self, moment):
        return self.get_queryset().upcoming(moment)

    def past(self, moment):
        return self.get_queryset().past(moment)

    def overlapping(self, start, end):
        return self.get_queryset().overlapping(start, end)


class Event(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    start = models.DateTimeField(verbose_name="Début")
    # Inclusive -- the last moment the event is happening. Defaults to `start`
    # on save() (see below), so every consumer can rely on it never being NULL.
    end = models.DateTimeField(null=True, blank=True, verbose_name="Fin")
    all_day = models.BooleanField(default=False, verbose_name="Journée entière")
    # Free-text only -- reuses the address picker/geocoding, same as Chalet.
    # No optional Chalet FK (resolved decision, see sprint-brief.md).
    location = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu")
    # Field names are load-bearing: AddressAutocompleteInput hardcodes
    # data-lat-target="id_latitude" / data-lon-target="id_longitude".
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Longitude")
    organisers = models.ManyToManyField(
        Person,
        blank=True,
        related_name="organised_events",
        verbose_name="Organisateurs·rices",
    )
    groups = models.ManyToManyField(
        Group,
        through="EventGroupAccess",
        blank=True,
        related_name="events",
        verbose_name="Groupes autorisés",
    )
    created_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_events",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    # Reserved for 12.3 (event reminders) -- declared here so that item needs no
    # `events` migration of its own and can never collide with 12.2's Rsvp
    # migration. Never exposed on a form (editable=False).
    reminder_sent_at = models.DateTimeField(null=True, blank=True, editable=False, verbose_name="Rappel envoyé le")

    objects = EventManager()

    class Meta:
        ordering = ["start", "pk"]
        verbose_name = "Événement"
        verbose_name_plural = "Événements"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.end is None:
            self.end = self.start
        if self.all_day:
            local_start = timezone.localtime(self.start)
            local_end = timezone.localtime(self.end)
            self.start = local_start.replace(hour=0, minute=0, second=0, microsecond=0)
            self.end = local_end.replace(hour=23, minute=59, second=59, microsecond=0)
        super().save(*args, **kwargs)

    def clean(self):
        if self.end is not None and self.start is not None and self.end < self.start:
            raise ValidationError({"end": "La date de fin doit être postérieure à la date de début."})


class EventGroupAccess(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name="Événement")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name="Groupe")

    class Meta:
        verbose_name = "Accès groupe à événement"
        verbose_name_plural = "Accès groupes à événements"
        constraints = [
            models.UniqueConstraint(fields=["event", "group"], name="unique_event_group_access"),
        ]

    def __str__(self):
        return f"{self.event} — {self.group}"


RSVP_CHOICES = [
    ("yes", "Oui"),
    ("no", "Non"),
    ("maybe", "Peut-être"),
]


class Rsvp(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps", verbose_name="Événement")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="rsvps", verbose_name="Personne")
    response = models.CharField(max_length=10, choices=RSVP_CHOICES, verbose_name="Réponse")
    # Additional guests beyond the person themself -- not the total headcount.
    guest_count = models.PositiveSmallIntegerField(default=0, verbose_name="Accompagnants")
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Participation"
        verbose_name_plural = "Participations"
        constraints = [
            models.UniqueConstraint(fields=["event", "person"], name="unique_event_person_rsvp"),
        ]

    def __str__(self):
        return f"{self.person} — {self.get_response_display()} ({self.event})"
