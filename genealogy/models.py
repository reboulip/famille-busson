from django.contrib.postgres.search import SearchVectorField
from django.db import models

from annuaire.models import Person


class StoryManager(models.Manager):
    def chronological(self):
        """Oldest first -- a life story timeline reads chronologically.
        Undated stories sort last rather than being mixed in without a date hint,
        same nulls_last discipline as PhotoManager.chronological()."""
        return self.get_queryset().order_by(models.F("date").asc(nulls_last=True), "pk")


class Story(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="stories", verbose_name="Personne")
    title = models.CharField(max_length=200, verbose_name="Titre")
    body = models.TextField(blank=True, default="", verbose_name="Récit")
    date = models.DateField(null=True, blank=True, verbose_name="Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    photos = models.ManyToManyField(
        "photos.Photo", through="StoryPhoto", blank=True, related_name="stories", verbose_name="Photos"
    )
    created_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    search_vector = SearchVectorField(null=True, editable=False, verbose_name="Vecteur de recherche")
    search_text = models.TextField(blank=True, default="", editable=False, verbose_name="Texte de recherche")

    objects = StoryManager()

    class Meta:
        verbose_name = "Récit"
        verbose_name_plural = "Récits"

    def __str__(self):
        return self.title


class StoryPhoto(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="story_photos", verbose_name="Récit")
    photo = models.ForeignKey("photos.Photo", on_delete=models.CASCADE, related_name="+", verbose_name="Photo")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "Photo d'un récit"
        verbose_name_plural = "Photos d'un récit"
        constraints = [
            models.UniqueConstraint(fields=["story", "photo"], name="unique_story_photo"),
        ]

    def __str__(self):
        return f"{self.photo} dans {self.story}"
