import os

from django.contrib.auth.models import Group
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
    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    body = models.TextField(verbose_name=_("Contenu"))
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

    @property
    def accent(self) -> str:
        """The first accented tag's accent, or "" -- drives the post card's
        left-bar colour (fb-post-card--{{ accent }}), generalizing what used
        to be a hardcoded rule keyed on the retired post_type field."""
        tag = self.tags.filter(accent__gt="").order_by("name").first()
        return tag.accent if tag else ""


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


class Bulletin(SoftDeleteModelMixin, models.Model):
    """A scanned family bulletin/newsletter, imported from a validated JSON +
    images package. `data` is the source of truth for rendering -- the other
    fields exist only for listing/ordering/search."""

    STATUS_CHOICES = [
        ("draft", _("Brouillon")),
        ("published", _("Publié")),
    ]

    document_id = models.CharField(max_length=50, unique=True, verbose_name=_("Identifiant"))
    series_code = models.CharField(max_length=20, verbose_name=_("Série"))
    series_title = models.CharField(max_length=200, verbose_name=_("Titre de la série"))
    issue_number = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Numéro"))
    issue_label = models.CharField(max_length=50, blank=True, default="", verbose_name=_("Numéro (libellé)"))
    date_value = models.CharField(max_length=10, verbose_name=_("Date (ISO partielle)"))
    sort_date = models.DateField(verbose_name=_("Date de tri"))
    title = models.CharField(max_length=255, verbose_name=_("Titre"))
    summary = models.TextField(blank=True, default="", verbose_name=_("Résumé"))
    data = models.JSONField(verbose_name=_("Contenu (JSON)"))
    schema_version = models.CharField(max_length=10, verbose_name=_("Version du schéma"))
    source_sha256 = models.CharField(max_length=64, blank=True, default="", verbose_name=_("SHA-256 de la source"))
    source_file_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Nom du fichier source")
    )
    source_pdf = models.FileField(
        upload_to="bulletins/sources/", blank=True, null=True, verbose_name=_("PDF original")
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="published", verbose_name=_("Statut"))
    groups = models.ManyToManyField(
        Group,
        through="BulletinGroupAccess",
        blank=True,
        related_name="bulletins",
        verbose_name=_("Groupes autorisés"),
    )
    imported_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Importé par")
    )
    imported_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'import"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Dernière modification"))
    search_vector = SearchVectorField(null=True, editable=False, verbose_name=_("Vecteur de recherche"))
    search_text = models.TextField(blank=True, default="", editable=False, verbose_name=_("Texte de recherche"))

    class Meta:
        ordering = ["-sort_date"]
        verbose_name = _("Bulletin")
        verbose_name_plural = _("Bulletins")
        default_manager_name = "objects"

    def __str__(self):
        return self.title

    @property
    def cover_image(self):
        """The listing thumbnail: the package's declared cover/masthead image,
        falling back to whichever image sorts first. Reads from an already
        `prefetch_related("images")`-loaded cache when there is one, instead
        of issuing a fresh filtered query per bulletin in a list."""
        images = list(self.images.all())
        if not images:
            return None
        cover_id = self.data.get("cover_image") or self.data.get("masthead_image")
        for image in images:
            if image.image_id == cover_id:
                return image
        return images[0]


class BulletinImage(models.Model):
    bulletin = models.ForeignKey(Bulletin, on_delete=models.CASCADE, related_name="images", verbose_name=_("Bulletin"))
    image_id = models.CharField(max_length=80, verbose_name=_("Identifiant"))
    file = models.ImageField(upload_to="bulletins/", verbose_name=_("Fichier"))
    kind = models.CharField(max_length=20, verbose_name=_("Type"))
    width = models.PositiveIntegerField(verbose_name=_("Largeur"))
    height = models.PositiveIntegerField(verbose_name=_("Hauteur"))
    sha256 = models.CharField(max_length=64, verbose_name=_("SHA-256"))

    class Meta:
        ordering = ["image_id"]
        verbose_name = _("Image de bulletin")
        verbose_name_plural = _("Images de bulletin")
        constraints = [
            models.UniqueConstraint(fields=["bulletin", "image_id"], name="unique_bulletin_image_id"),
        ]

    def __str__(self):
        return self.image_id


class BulletinGroupAccess(models.Model):
    bulletin = models.ForeignKey(Bulletin, on_delete=models.CASCADE, verbose_name=_("Bulletin"))
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name=_("Groupe"))

    class Meta:
        verbose_name = _("Accès groupe à bulletin")
        verbose_name_plural = _("Accès groupes à bulletins")
        constraints = [
            models.UniqueConstraint(fields=["bulletin", "group"], name="unique_bulletin_group_access"),
        ]

    def __str__(self):
        return f"{self.bulletin} — {self.group}"


class BulletinImport(models.Model):
    """One uploaded bulletin package, staged for review. Nothing here is
    visible outside the staging tables until a staff member explicitly
    applies it -- see publications/bulletin_import.py."""

    STATUS_CHOICES = [
        ("pending_review", _("En attente de relecture")),
        ("applied", _("Appliqué")),
        ("discarded", _("Abandonné")),
    ]

    uploaded_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Déposé par")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de dépôt"))
    original_filename = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Nom du fichier"))
    document_id = models.CharField(max_length=50, blank=True, default="", verbose_name=_("Identifiant"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending_review", verbose_name=_("Statut")
    )
    data = models.JSONField(default=dict, verbose_name=_("Contenu (JSON)"))
    validation_report = models.JSONField(default=dict, verbose_name=_("Rapport de validation"))
    source_pdf = models.FileField(
        upload_to="bulletins/_imports/", blank=True, null=True, verbose_name=_("PDF original")
    )

    class Meta:
        verbose_name = _("Import de bulletin")
        verbose_name_plural = _("Imports de bulletin")

    def __str__(self):
        return self.document_id or self.original_filename or f"Import #{self.pk}"

    @property
    def can_publish(self) -> bool:
        return self.status == "pending_review" and not self.validation_report.get("errors")


class BulletinImportImage(models.Model):
    bulletin_import = models.ForeignKey(
        BulletinImport, on_delete=models.CASCADE, related_name="images", verbose_name=_("Import")
    )
    image_id = models.CharField(max_length=80, verbose_name=_("Identifiant"))
    file = models.ImageField(upload_to="bulletins/_imports/", verbose_name=_("Fichier"))
    kind = models.CharField(max_length=20, verbose_name=_("Type"))
    width = models.PositiveIntegerField(verbose_name=_("Largeur"))
    height = models.PositiveIntegerField(verbose_name=_("Hauteur"))
    sha256 = models.CharField(max_length=64, verbose_name=_("SHA-256"))

    class Meta:
        ordering = ["image_id"]
        verbose_name = _("Image d'import de bulletin")
        verbose_name_plural = _("Images d'import de bulletin")

    def __str__(self):
        return self.image_id
