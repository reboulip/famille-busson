from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from annuaire.models import Person, Relation

from .citations import canonical_relation

# The claim vocabulary is the literal field names 13.1 introduced on Person/Relation,
# so a future GEDCOM export can map a claim straight to a tag with no translation
# table. Keep this in sync with annuaire.models.Person/Relation if those fields are
# ever renamed.
CLAIM_CHOICES = [
    ("birth_date", _("Date de naissance")),
    ("birth_place", _("Lieu de naissance")),
    ("death_date", _("Date de décès")),
    ("death_place", _("Lieu de décès")),
    ("start_date", _("Date de mariage")),
    ("end_date", _("Date de fin (relation)")),
    ("marriage_place", _("Lieu du mariage")),
]

SOURCE_KIND_CHOICES = [
    ("acte_civil", _("Acte d'état civil")),
    ("presse", _("Article de presse")),
    ("temoignage", _("Témoignage oral")),
    ("registre", _("Registre ou archive")),
    ("autre", _("Autre")),
]


class StoryManager(models.Manager):
    def chronological(self):
        """Oldest first -- a life story timeline reads chronologically.
        Undated stories sort last rather than being mixed in without a date hint,
        same nulls_last discipline as PhotoManager.chronological()."""
        return self.get_queryset().order_by(models.F("date").asc(nulls_last=True), "pk")


class Story(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="stories", verbose_name=_("Personne"))
    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    body = models.TextField(blank=True, default="", verbose_name=_("Récit"))
    date = models.DateField(null=True, blank=True, verbose_name=_("Date"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("Date de fin"))
    photos = models.ManyToManyField(
        "photos.Photo", through="StoryPhoto", blank=True, related_name="stories", verbose_name=_("Photos")
    )
    created_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Dernière modification"))
    search_vector = SearchVectorField(null=True, editable=False, verbose_name=_("Vecteur de recherche"))
    search_text = models.TextField(blank=True, default="", editable=False, verbose_name=_("Texte de recherche"))

    objects = StoryManager()

    class Meta:
        verbose_name = _("Récit")
        verbose_name_plural = _("Récits")

    def __str__(self):
        return self.title


class StoryPhoto(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="story_photos", verbose_name=_("Récit"))
    photo = models.ForeignKey("photos.Photo", on_delete=models.CASCADE, related_name="+", verbose_name=_("Photo"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Ordre"))

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = _("Photo d'un récit")
        verbose_name_plural = _("Photos d'un récit")
        constraints = [
            models.UniqueConstraint(fields=["story", "photo"], name="unique_story_photo"),
        ]

    def __str__(self):
        return f"{self.photo} dans {self.story}"


class Source(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    kind = models.CharField(max_length=20, choices=SOURCE_KIND_CHOICES, blank=True, default="", verbose_name=_("Type"))
    reference = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Référence"))
    repository = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu de conservation"))
    date = models.DateField(null=True, blank=True, verbose_name=_("Date"))
    url = models.URLField(blank=True, default="", verbose_name=_("Lien"))
    notes = models.TextField(blank=True, default="", verbose_name=_("Notes"))
    # The family archive already holds OCR'd scanned documents -- letting a
    # citation point at one avoids re-typing provenance that's already there.
    # Access-checked at render time via accessible_documents(viewer), never here.
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="genealogy_sources",
        verbose_name=_("Document associé"),
    )
    created_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Créé par")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Dernière modification"))

    class Meta:
        verbose_name = _("Source")
        verbose_name_plural = _("Sources")

    def __str__(self):
        return self.title


class Citation(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="citations", verbose_name=_("Source"))
    story = models.ForeignKey(
        Story, on_delete=models.CASCADE, null=True, blank=True, related_name="citations", verbose_name=_("Récit")
    )
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, null=True, blank=True, related_name="citations", verbose_name=_("Personne")
    )
    relation = models.ForeignKey(
        "annuaire.Relation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="citations",
        verbose_name=_("Relation"),
    )
    claim = models.CharField(
        max_length=40, choices=CLAIM_CHOICES, blank=True, default="", verbose_name=_("Donnée citée")
    )
    note = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Note"))

    class Meta:
        verbose_name = _("Citation")
        verbose_name_plural = _("Citations")
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
            raise ValidationError(_("Une citation doit cibler exactement un récit, une personne ou une relation."))
        if (self.person_id or self.relation_id) and not self.claim:
            raise ValidationError(
                {"claim": _("La donnée citée est obligatoire pour une citation sur une personne ou une relation.")}
            )
        if self.story_id and self.claim:
            raise ValidationError({"claim": _("Un récit ne cible pas une donnée précise ; laissez ce champ vide.")})


GEDCOM_IMPORT_STATUS_CHOICES = [
    ("pending_review", _("En attente de révision")),
    ("applied", _("Appliqué")),
    ("discarded", _("Abandonné")),
]

STAGED_INDIVIDUAL_DECISION_CHOICES = [
    ("create", _("Créer un nouveau profil")),
    ("merge", _("Fusionner avec un profil existant")),
    ("skip", _("Ignorer")),
]


class GedcomImport(models.Model):
    """One uploaded GEDCOM file, staged for review. Nothing here is written
    to Person/Relation until a staff member explicitly applies it -- see
    genealogy/gedcom/importer.py."""

    uploaded_by = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Déposé par")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de dépôt"))
    original_filename = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Nom du fichier"))
    status = models.CharField(
        max_length=20, choices=GEDCOM_IMPORT_STATUS_CHOICES, default="pending_review", verbose_name=_("Statut")
    )
    # Kept in the database, not on disk -- media/documents_data are what the
    # backup script archives; a file here would need scripts/backup.sh to
    # learn a third storage root for what's realistically a small text file.
    raw_content = models.TextField(verbose_name=_("Contenu brut"))

    class Meta:
        verbose_name = _("Import GEDCOM")
        verbose_name_plural = _("Imports GEDCOM")

    def __str__(self):
        return self.original_filename or f"Import #{self.pk}"


class StagedIndividual(models.Model):
    gedcom_import = models.ForeignKey(
        GedcomImport, on_delete=models.CASCADE, related_name="staged_individuals", verbose_name=_("Import")
    )
    source_xref = models.CharField(max_length=20, blank=True, default="", verbose_name=_("Référence GEDCOM"))
    first_name = models.CharField(max_length=100, blank=True, default="", verbose_name=_("Prénom"))
    last_name = models.CharField(max_length=100, blank=True, default="", verbose_name=_("Nom"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Date de naissance"))
    birth_place = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu de naissance"))
    death_date = models.DateField(null=True, blank=True, verbose_name=_("Date de décès"))
    death_place = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu de décès"))
    # Staff's chosen existing-person match, when decision == "merge".
    match_person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Profil correspondant"),
    )
    decision = models.CharField(
        max_length=10, choices=STAGED_INDIVIDUAL_DECISION_CHOICES, default="create", verbose_name=_("Décision")
    )
    # Filled in at apply time: the real Person this staged row resolved to
    # (a newly created one, or the merge target) -- lets StagedFamily
    # resolve its husband/wife/children xrefs to real Person pks.
    created_person = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Profil résultant")
    )

    class Meta:
        verbose_name = _("Individu importé")
        verbose_name_plural = _("Individus importés")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.source_xref})"


class StagedFamily(models.Model):
    gedcom_import = models.ForeignKey(
        GedcomImport, on_delete=models.CASCADE, related_name="staged_families", verbose_name=_("Import")
    )
    source_xref = models.CharField(max_length=20, blank=True, default="", verbose_name=_("Référence GEDCOM"))
    husband_xref = models.CharField(max_length=20, blank=True, default="", verbose_name=_("Référence de l'époux"))
    wife_xref = models.CharField(max_length=20, blank=True, default="", verbose_name=_("Référence de l'épouse"))
    children_xrefs = models.JSONField(default=list, blank=True, verbose_name=_("Références des enfants"))
    marriage_date = models.DateField(null=True, blank=True, verbose_name=_("Date de mariage"))
    marriage_place = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Lieu du mariage"))
    divorce_date = models.DateField(null=True, blank=True, verbose_name=_("Date de divorce"))

    class Meta:
        verbose_name = _("Famille importée")
        verbose_name_plural = _("Familles importées")

    def __str__(self):
        return f"Famille {self.source_xref}"
