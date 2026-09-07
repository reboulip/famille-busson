import os

from django.db import models

from annuaire.models import Person

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
PDF_EXTENSIONS = {".pdf"}


class Tag(models.Model):
    ACCENT_CHOICES = [
        ("", "Aucun"),
        ("gold", "Doré"),
        ("accent", "Alpenglow"),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name="Étiquette")
    accent = models.CharField(max_length=10, choices=ACCENT_CHOICES, blank=True, verbose_name="Accent")

    class Meta:
        ordering = ["name"]
        verbose_name = "Étiquette"
        verbose_name_plural = "Étiquettes"

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    # post_type ("Busson connection") and tags coexist deliberately: Phase 16.2
    # migrates post_type onto a tag and removes this field then, not now.
    POST_TYPE_CHOICES = [
        ("BC", "Busson connection"),
        ("NORMAL", "Publication normale"),
    ]

    title = models.CharField(max_length=200, verbose_name="Titre")
    body = models.TextField(verbose_name="Contenu")
    post_type = models.CharField(
        max_length=10,
        choices=POST_TYPE_CHOICES,
        default="NORMAL",
        verbose_name="Type de publication",
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="posts",
        verbose_name="Étiquettes",
    )
    authors = models.ManyToManyField(
        Person,
        related_name="blog_posts",
        verbose_name="Auteur(s)",
    )
    documents = models.ManyToManyField(
        "documents.Document",
        blank=True,
        related_name="publications",
        verbose_name="Documents liés",
    )
    albums = models.ManyToManyField(
        "photos.Album",
        blank=True,
        related_name="publications",
        verbose_name="Albums liés",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Publication"
        verbose_name_plural = "Publications"

    def __str__(self):
        return self.title


class Attachment(models.Model):
    post = models.ForeignKey(
        BlogPost,
        related_name="attachments",
        on_delete=models.CASCADE,
        verbose_name="Publication",
    )
    file = models.FileField(upload_to="publications/", verbose_name="Fichier")
    caption = models.CharField(max_length=255, blank=True, default="", verbose_name="Légende")
    is_image = models.BooleanField(default=False, verbose_name="Est une image")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de téléversement")

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"

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
        verbose_name="Publication",
    )
    author = models.ForeignKey(
        Person,
        related_name="comments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Auteur",
    )
    body = models.TextField(verbose_name="Commentaire")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"

    def __str__(self):
        return f"{self.author or 'Anonyme'} sur {self.post}"
