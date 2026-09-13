import os

from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _

from annuaire.models import Person
from annuaire.soft_delete import SoftDeleteModelMixin

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
PDF_EXTENSIONS = {".pdf"}


class Tag(models.Model):
    ACCENT_CHOICES = [
        ("", _("Aucun")),
        ("gold", _("Doré")),
        ("accent", _("Alpenglow")),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name=_("Étiquette"))
    accent = models.CharField(max_length=10, choices=ACCENT_CHOICES, blank=True, verbose_name=_("Accent"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Étiquette")
        verbose_name_plural = _("Étiquettes")

    def __str__(self):
        return self.name


class BlogPost(SoftDeleteModelMixin, models.Model):
    # post_type ("Busson connection") and tags coexist deliberately: Phase 16.2
    # migrates post_type onto a tag and removes this field then, not now.
    POST_TYPE_CHOICES = [
        ("BC", _("Busson connection")),
        ("NORMAL", _("Publication normale")),
    ]

    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    body = models.TextField(verbose_name=_("Contenu"))
    post_type = models.CharField(
        max_length=10,
        choices=POST_TYPE_CHOICES,
        default="NORMAL",
        verbose_name=_("Type de publication"),
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="posts",
        verbose_name=_("Étiquettes"),
    )
    authors = models.ManyToManyField(
        Person,
        related_name="blog_posts",
        verbose_name=_("Auteur(s)"),
    )
    documents = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="publications",
        verbose_name=_("Documents liés"),
    )
    albums = models.ManyToManyField(
        "photos.Album",
        blank=True,
        related_name="publications",
        verbose_name=_("Albums liés"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Dernière modification"))
    search_vector = SearchVectorField(null=True, editable=False, verbose_name=_("Vecteur de recherche"))
    search_text = models.TextField(blank=True, default="", editable=False, verbose_name=_("Texte de recherche"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Publication")
        verbose_name_plural = _("Publications")
        default_manager_name = "objects"

    def __str__(self):
        return self.title


class Attachment(models.Model):
    post = models.ForeignKey(
        BlogPost,
        related_name="attachments",
        on_delete=models.CASCADE,
        verbose_name=_("Publication"),
    )
    file = models.FileField(upload_to="publications/", verbose_name=_("Fichier"))
    caption = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Légende"))
    is_image = models.BooleanField(default=False, verbose_name=_("Est une image"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de téléversement"))

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = _("Pièce jointe")
        verbose_name_plural = _("Pièces jointes")

    def __str__(self):
        return self.caption or self.filename

    def save(self, *args, **kwargs):
        extension = os.path.splitext(self.file.name)[1].lower()
        self.is_image = extension in IMAGE_EXTENSIONS
        super().save(*args, **kwargs)

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def is_pdf(self) -> bool:
        return os.path.splitext(self.file.name)[1].lower() in PDF_EXTENSIONS


class Comment(models.Model):
    post = models.ForeignKey(
        BlogPost,
        related_name="comments",
        on_delete=models.CASCADE,
        verbose_name=_("Publication"),
    )
    author = models.ForeignKey(
        Person,
        related_name="comments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Auteur"),
    )
    body = models.TextField(verbose_name=_("Commentaire"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Commentaire")
        verbose_name_plural = _("Commentaires")

    def __str__(self):
        return f"{self.author or 'Anonyme'} sur {self.post}"
