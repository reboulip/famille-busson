from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models

from annuaire.models import Person, Relation

from .citations import canonical_relation

# The claim vocabulary is the literal field names 13.1 introduced on Person/Relation,
# so a future GEDCOM export can map a claim straight to a tag with no translation
# table. Keep this in sync with annuaire.models.Person/Relation if those fields are
# ever renamed.
CLAIM_CHOICES = [
    ("birth_date", "Date de naissance"),
    ("birth_place", "Lieu de naissance"),
    ("death_date", "Date de décès"),
    ("death_place", "Lieu de décès"),
    ("start_date", "Date de mariage"),
    ("end_date", "Date de fin (relation)"),
    ("marriage_place", "Lieu du mariage"),
]

SOURCE_KIND_CHOICES = [
    ("acte_civil", "Acte d'état civil"),
    ("presse", "Article de presse"),
    ("temoignage", "Témoignage oral"),
    ("registre", "Registre ou archive"),
    ("autre", "Autre"),
]


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


class Source(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    kind = models.CharField(max_length=20, choices=SOURCE_KIND_CHOICES, blank=True, default="", verbose_name="Type")
    reference = models.CharField(max_length=255, blank=True, default="", verbose_name="Référence")
    repository = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu de conservation")
    date = models.DateField(null=True, blank=True, verbose_name="Date")
    url = models.URLField(blank=True, default="", verbose_name="Lien")
    notes = models.TextField(blank=True, default="", verbose_name="Notes")
    # The family archive already holds OCR'd scanned documents -- letting a
    # citation point at one avoids re-typing provenance that's already there.
    # Access-checked at render time via accessible_documents(viewer), never here.
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="genealogy_sources",
        verbose_name="Document associé",
    )
    created_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Source"
        verbose_name_plural = "Sources"

    def __str__(self):
        return self.title


class Citation(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="citations", verbose_name="Source")
    story = models.ForeignKey(
        Story, on_delete=models.CASCADE, null=True, blank=True, related_name="citations", verbose_name="Récit"
    )
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, null=True, blank=True, related_name="citations", verbose_name="Personne"
    )
    relation = models.ForeignKey(
        "annuaire.Relation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="citations",
        verbose_name="Relation",
    )
    claim = models.CharField(max_length=40, choices=CLAIM_CHOICES, blank=True, default="", verbose_name="Donnée citée")
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="Note")

    class Meta:
        verbose_name = "Citation"
        verbose_name_plural = "Citations"
        constraints = [
            # NULL columns are never equal to each other in SQL, so this only ever
            # rejects a true duplicate (same source, same single target, same
            # claim) -- it can't catch two citations that both target different
            # NULL columns, which is every row here by construction (clean()
            # enforces exactly one of story/person/relation).
            models.UniqueConstraint(
                fields=["source", "story", "person", "relation", "claim"], name="unique_citation_target"
            ),
        ]

    def __str__(self):
        target = self.story or self.person or self.relation
        return f"{self.source} → {target}"

    def save(self, *args, **kwargs):
        if self.relation_id is not None:
            current: Relation = Relation.objects.get(pk=self.relation_id)
            self.relation = canonical_relation(current)
        super().save(*args, **kwargs)

    def clean(self):
        target_count = sum(1 for value in (self.story_id, self.person_id, self.relation_id) if value is not None)
        if target_count != 1:
            raise ValidationError("Une citation doit cibler exactement un récit, une personne ou une relation.")
        if (self.person_id or self.relation_id) and not self.claim:
            raise ValidationError(
                {"claim": "La donnée citée est obligatoire pour une citation sur une personne ou une relation."}
            )
        if self.story_id and self.claim:
            raise ValidationError({"claim": "Un récit ne cible pas une donnée précise ; laissez ce champ vide."})


GEDCOM_IMPORT_STATUS_CHOICES = [
    ("pending_review", "En attente de révision"),
    ("applied", "Appliqué"),
    ("discarded", "Abandonné"),
]

STAGED_INDIVIDUAL_DECISION_CHOICES = [
    ("create", "Créer un nouveau profil"),
    ("merge", "Fusionner avec un profil existant"),
    ("skip", "Ignorer"),
]


class GedcomImport(models.Model):
    """One uploaded GEDCOM file, staged for review. Nothing here is written
    to Person/Relation until a staff member explicitly applies it -- see
    genealogy/gedcom/importer.py."""

    uploaded_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Déposé par"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de dépôt")
    original_filename = models.CharField(max_length=255, blank=True, default="", verbose_name="Nom du fichier")
    status = models.CharField(
        max_length=20, choices=GEDCOM_IMPORT_STATUS_CHOICES, default="pending_review", verbose_name="Statut"
    )
    # Kept in the database, not on disk -- media/documents_data are what the
    # backup script archives; a file here would need scripts/backup.sh to
    # learn a third storage root for what's realistically a small text file.
    raw_content = models.TextField(verbose_name="Contenu brut")

    class Meta:
        verbose_name = "Import GEDCOM"
        verbose_name_plural = "Imports GEDCOM"

    def __str__(self):
        return self.original_filename or f"Import #{self.pk}"


class StagedIndividual(models.Model):
    gedcom_import = models.ForeignKey(
        GedcomImport, on_delete=models.CASCADE, related_name="staged_individuals", verbose_name="Import"
    )
    source_xref = models.CharField(max_length=20, blank=True, default="", verbose_name="Référence GEDCOM")
    first_name = models.CharField(max_length=100, blank=True, default="", verbose_name="Prénom")
    last_name = models.CharField(max_length=100, blank=True, default="", verbose_name="Nom")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    birth_place = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu de naissance")
    death_date = models.DateField(null=True, blank=True, verbose_name="Date de décès")
    death_place = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu de décès")
    # Staff's chosen existing-person match, when decision == "merge".
    match_person = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Profil correspondant"
    )
    decision = models.CharField(
        max_length=10, choices=STAGED_INDIVIDUAL_DECISION_CHOICES, default="create", verbose_name="Décision"
    )
    # Filled in at apply time: the real Person this staged row resolved to
    # (a newly created one, or the merge target) -- lets StagedFamily
    # resolve its husband/wife/children xrefs to real Person pks.
    created_person = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Profil résultant"
    )

    class Meta:
        verbose_name = "Individu importé"
        verbose_name_plural = "Individus importés"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.source_xref})"


class StagedFamily(models.Model):
    gedcom_import = models.ForeignKey(
        GedcomImport, on_delete=models.CASCADE, related_name="staged_families", verbose_name="Import"
    )
    source_xref = models.CharField(max_length=20, blank=True, default="", verbose_name="Référence GEDCOM")
    husband_xref = models.CharField(max_length=20, blank=True, default="", verbose_name="Référence de l'époux")
    wife_xref = models.CharField(max_length=20, blank=True, default="", verbose_name="Référence de l'épouse")
    children_xrefs = models.JSONField(default=list, blank=True, verbose_name="Références des enfants")
    marriage_date = models.DateField(null=True, blank=True, verbose_name="Date de mariage")
    marriage_place = models.CharField(max_length=255, blank=True, default="", verbose_name="Lieu du mariage")
    divorce_date = models.DateField(null=True, blank=True, verbose_name="Date de divorce")

    class Meta:
        verbose_name = "Famille importée"
        verbose_name_plural = "Familles importées"

    def __str__(self):
        return f"Famille {self.source_xref}"
