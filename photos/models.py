import os

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models

from annuaire.models import Person

from .storage import get_photo_storage
from .validators import validate_photo_extension, validate_photo_size

DERIVATIVE_STATUS_CHOICES = [
    ("pending", "En attente"),
    ("done", "Terminé"),
    ("error", "Erreur"),
]


class PhotoManager(models.Manager):
    def chronological(self):
        """Canonical ordering for every photo listing/grid/lightbox/prev-next in
        the photothèque -- taken_at is null until 10.3's derivative generation
        extracts EXIF, so this degrades gracefully to upload order. Never
        re-spell this ordering inline elsewhere."""
        return self.get_queryset().order_by(models.F("taken_at").desc(nulls_last=True), "pk")


class Album(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    date_start = models.DateField(null=True, blank=True, verbose_name="Date de début")
    date_end = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    cover = models.ForeignKey(
        "photos.Photo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Photo de couverture",
    )
    groups = models.ManyToManyField(
        Group,
        through="AlbumGroupAccess",
        blank=True,
        related_name="photo_albums",
        verbose_name="Groupes autorisés",
    )
    created_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_albums",
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Album"
        verbose_name_plural = "Albums"

    def __str__(self):
        return self.title

    def clean(self):
        # A cover from another album would leak that album's photo onto this
        # one's card -- guard at the model level in addition to AlbumForm
        # scoping the field's queryset to the album's own photos.
        if self.cover_id is not None and self.pk is not None and self.cover.album_id != self.pk:
            raise ValidationError({"cover": "La photo de couverture doit appartenir à cet album."})


class AlbumGroupAccess(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, verbose_name="Album")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name="Groupe")

    class Meta:
        verbose_name = "Accès groupe à album"
        verbose_name_plural = "Accès groupes à albums"
        constraints = [
            models.UniqueConstraint(fields=["album", "group"], name="unique_album_group_access"),
        ]

    def __str__(self):
        return f"{self.album} — {self.group}"


class Photo(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="photos", verbose_name="Album")
    file = models.ImageField(
        upload_to="originals/",
        storage=get_photo_storage,
        validators=[validate_photo_extension, validate_photo_size],
        verbose_name="Fichier",
    )
    caption = models.CharField(max_length=255, blank=True, default="", verbose_name="Légende")
    taken_at = models.DateTimeField(null=True, blank=True, verbose_name="Pris le")
    uploaded_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_photos",
        verbose_name="Déposé par",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de téléversement")
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name="Largeur")
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name="Hauteur")

    # Derivative fields -- populated asynchronously (see photos/tasks.py, a later
    # item), defined here so PhotoFileView can declare all three variants from
    # day one and fall back to the original while a derivative is still pending.
    thumbnail = models.ImageField(
        upload_to="thumbnails/", storage=get_photo_storage, null=True, blank=True, verbose_name="Vignette"
    )
    web = models.ImageField(
        upload_to="web/", storage=get_photo_storage, null=True, blank=True, verbose_name="Rendu web"
    )
    derivative_status = models.CharField(
        max_length=20,
        choices=DERIVATIVE_STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Statut des dérivés",
    )
    derivative_error = models.CharField(max_length=255, blank=True, default="", verbose_name="Erreur de dérivés")
    derivatives_generated_at = models.DateTimeField(null=True, blank=True, verbose_name="Dérivés générés le")

    objects = PhotoManager()

    class Meta:
        ordering = ["uploaded_at", "pk"]
        verbose_name = "Photo"
        verbose_name_plural = "Photos"

    def __str__(self):
        return self.caption or self.filename

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class PersonTag(models.Model):
    """Identifies a Person in a Photo. The region box is stored (normalized
    0-1 floats, all-or-none) but not yet drawn anywhere -- a future item adds
    the drawing UI. Any member who can access the photo's album may tag or
    untag people (the same collaborative posture as document/relation
    editing on this site); tagged_by records who did it."""

    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="person_tags", verbose_name="Photo")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="tagged_photos", verbose_name="Personne")
    region_x = models.FloatField(null=True, blank=True, verbose_name="Position X")
    region_y = models.FloatField(null=True, blank=True, verbose_name="Position Y")
    region_width = models.FloatField(null=True, blank=True, verbose_name="Largeur de la zone")
    region_height = models.FloatField(null=True, blank=True, verbose_name="Hauteur de la zone")
    tagged_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Identifié par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'identification")

    class Meta:
        verbose_name = "Personne identifiée sur une photo"
        verbose_name_plural = "Personnes identifiées sur une photo"
        constraints = [
            models.UniqueConstraint(fields=["photo", "person"], name="unique_photo_person_tag"),
        ]

    def __str__(self):
        return f"{self.person} sur {self.photo}"

    def clean(self):
        region_fields = [self.region_x, self.region_y, self.region_width, self.region_height]
        if any(f is not None for f in region_fields) and not all(f is not None for f in region_fields):
            raise ValidationError(
                "La zone de la photo doit être définie entièrement (les quatre valeurs) ou pas du tout."
            )
