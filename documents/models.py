import os

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from annuaire.models import Person

from .storage import get_document_storage
from .validators import validate_document_extension, validate_document_size

EXTRACTION_STATUS_CHOICES = [
    ("pending", "En attente"),
    ("done", "Terminé"),
    ("unsupported", "Non pris en charge"),
    ("error", "Erreur"),
]

MAX_CATEGORY_DEPTH = 5


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
        verbose_name="Catégorie parente",
    )
    description = models.TextField(blank=True, default="", verbose_name="Description")
    groups = models.ManyToManyField(
        Group,
        through="CategoryGroupAccess",
        blank=True,
        related_name="document_categories",
        verbose_name="Groupes autorisés",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.name

    def clean(self):
        if self.parent_id is None:
            return
        if self.pk is not None and self.parent_id == self.pk:
            raise ValidationError({"parent": "Une catégorie ne peut pas être sa propre catégorie parente."})
        visited = {self.pk} if self.pk is not None else set()
        node = self.parent
        depth = 1
        while node is not None:
            if node.pk in visited:
                raise ValidationError({"parent": "Cette hiérarchie de catégories contient une boucle."})
            visited.add(node.pk)
            depth += 1
            if depth > MAX_CATEGORY_DEPTH:
                raise ValidationError(
                    {"parent": f"La hiérarchie des catégories ne peut pas dépasser {MAX_CATEGORY_DEPTH} niveaux."}
                )
            node = node.parent


class CategoryGroupAccess(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Catégorie")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name="Groupe")

    class Meta:
        verbose_name = "Accès groupe à catégorie"
        verbose_name_plural = "Accès groupes à catégories"
        constraints = [
            models.UniqueConstraint(fields=["category", "group"], name="unique_category_group_access"),
        ]

    def __str__(self):
        return f"{self.category} — {self.group}"


def ancestor_has_groups(category):
    """Also used by documents/forms.py's CategoryForm.clean() to surface this
    invariant as a normal form error -- a ModelForm's save_m2m() only runs
    after the main object is already saved, too late for the m2m_changed
    receiver below to become anything but an uncaught 500."""
    node = category.parent
    while node is not None:
        if node.groups.exists():
            return True
        node = node.parent
    return False


def descendant_has_groups(category):
    for child in category.children.all():
        if child.groups.exists() or descendant_has_groups(child):
            return True
    return False


@receiver(m2m_changed, sender=Category.groups.through)
def validate_category_group_restriction(sender, instance, action, **kwargs):
    """A category may only restrict access directly if the whole ancestry is
    public, and if no descendant already restricts independently -- a
    restricted category's descendants inherit its groups rather than setting
    their own (see documents/access.py's effective_groups())."""
    if action != "pre_add":
        return
    if ancestor_has_groups(instance):
        raise ValidationError(
            "Impossible de restreindre cette catégorie : une catégorie parente restreint déjà "
            "l'accès, et cette restriction s'applique à toute sa descendance."
        )
    if descendant_has_groups(instance):
        raise ValidationError(
            "Impossible de restreindre cette catégorie : une sous-catégorie restreint déjà "
            "l'accès de façon indépendante."
        )


class Document(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="documents", verbose_name="Catégorie"
    )
    document_date = models.DateField(null=True, blank=True, verbose_name="Date du document")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    uploaded_by = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="Déposé par",
    )
    redactor = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redacted_documents",
        verbose_name="Rédigé par",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.title


class DocumentFile(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="files", verbose_name="Document")
    file = models.FileField(
        upload_to="files/",
        storage=get_document_storage,
        validators=[validate_document_extension, validate_document_size],
        verbose_name="Fichier",
    )
    caption = models.CharField(max_length=255, blank=True, default="", verbose_name="Légende")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de téléversement")
    extracted_text = models.TextField(blank=True, default="", verbose_name="Texte extrait")
    extraction_status = models.CharField(
        max_length=20,
        choices=EXTRACTION_STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Statut d'extraction",
    )
    extraction_error = models.CharField(max_length=255, blank=True, default="", verbose_name="Erreur d'extraction")
    extracted_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'extraction")
    ocr_used = models.BooleanField(default=False, verbose_name="OCR utilisé")
    thumbnail = models.ImageField(
        upload_to="thumbnails/",
        storage=get_document_storage,
        null=True,
        blank=True,
        verbose_name="Vignette",
    )

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Fichier"
        verbose_name_plural = "Fichiers"

    def __str__(self):
        return self.caption or self.filename

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def preview_kind(self):
        from documents.previews import preview_kind

        return preview_kind(self.file.name)
