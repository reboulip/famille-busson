"""Personal data export -- what the site holds on a given Person, as a single
downloadable archive.

Like annuaire/person_merge.py, this is not a generic reflection loop over
Person._meta: each relation needs its own access scoping (a document/photo/
event category can be group-restricted; présences, publications and
comments are not). Every relation is enumerated explicitly in
PERSONAL_DATA_RELATIONS / PERSONAL_DATA_HIDDEN_RELATIONS, and
test_personal_data_meta_guard_covers_every_relation
(annuaire/tests/test_personal_data_export.py) is the actual safety net: it
walks Person._meta.get_fields(include_hidden=True), mirroring
person_merge.py's own guard, so a new FK/M2M onto Person can't silently
escape the export.

Scope (see sprint-brief.md, Phase 14): metadata and in-app links only, plus
the member's own profile photo -- no embedded document/photo/attachment
bytes. Built synchronously; no async job, no new storage surface.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Account, Person, Relation


class RetentionPolicy(StrEnum):
    """Placeholder for 14.2's anonymisation policy -- declared here so both
    items share one vocabulary, but only consumed starting with 14.2."""

    KEEP = "keep"
    ANONYMISE = "anonymise"
    DELETE = "delete"


@dataclass(frozen=True)
class DataCategory:
    key: str
    label: str
    note: str
    collect: Callable[[Person, Account], list[dict]]
    retention: RetentionPolicy = RetentionPolicy.KEEP


# Every visible reverse accessor name and forward M2M this module accounts
# for. Mirrors person_merge.py's HANDLED_RELATIONS in spirit (independently
# maintained -- export and merge have different concerns), checked by
# test_personal_data_meta_guard_covers_every_relation.
PERSONAL_DATA_RELATIONS: set[str] = {
    "owners",  # forward self-M2M -> comptes_geres
    "managed_profiles",  # reverse of owners -> comptes_geres
    "settings",  # O2O -> parametres
    "ascending_relations",  # Relation.person1 -> relations_familiales
    "descending_relations",  # Relation.person2 -> relations_familiales
    "owned_chalets",  # Chalet.owners M2M -> chalets
    "presencepsv_set",  # PresencePSV.person -> presences
    "blog_posts",  # BlogPost.authors M2M -> publications
    "comments",  # Comment.author -> commentaires
    "documents",  # Document.uploaded_by -> documents
    "redacted_documents",  # Document.redactor -> documents
    "created_albums",  # Album.created_by -> photos
    "uploaded_photos",  # Photo.uploaded_by -> photos
    "tagged_photos",  # PersonTag.person -> photos
    "created_events",  # Event.created_by -> evenements
    "organised_events",  # Event.organisers M2M -> evenements
    "rsvps",  # Rsvp.person -> evenements
    "stories",  # genealogy.Story.person -> genealogie
    "citations",  # genealogy.Citation.person -> genealogie
}

# Hidden relations (related_name="+") have no accessor name, tracked by
# (app_label, model_name, field_name) instead -- these are actions the
# subject took on someone else's record, not data about the subject.
PERSONAL_DATA_HIDDEN_RELATIONS: set[tuple[str, str, str]] = {
    ("photos", "persontag", "tagged_by"),  # -> photos
    ("genealogy", "story", "created_by"),  # -> genealogie
    ("genealogy", "source", "created_by"),  # -> genealogie
    ("genealogy", "gedcomimport", "uploaded_by"),  # -> genealogie
    ("genealogy", "stagedindividual", "match_person"),  # -> genealogie
    ("genealogy", "stagedindividual", "created_person"),  # -> genealogie
}


def _collect_profil(person: Person, viewer: Account) -> list[dict]:
    return [
        {
            "prenom": person.first_name,
            "nom": person.last_name,
            "email": person.email or "",
            "telephone": person.phone_number or "",
            "adresse_postale": person.postal_address or "",
            "latitude": str(person.latitude) if person.latitude is not None else "",
            "longitude": str(person.longitude) if person.longitude is not None else "",
            "date_naissance": person.birth_date.isoformat() if person.birth_date else "",
            "lieu_naissance": person.birth_place or "",
            "decede": person.deceased,
            "date_deces": person.death_date.isoformat() if person.death_date else "",
            "lieu_deces": person.death_place or "",
            "description": person.description or "",
            "confidentialite_export": person.export_privacy,
            "photo_profil": "photo-profil" if person.profile_photo else "",
            "cree_le": person.created_at.isoformat(),
            "lien": reverse("personne-detail", args=[person.pk]),
        }
    ]


def _collect_relations_familiales(person: Person, viewer: Account) -> list[dict]:
    rows = []
    qs = Relation.objects.filter(Q(person1=person) | Q(person2=person)).select_related("person1", "person2")
    for rel in qs:
        other = rel.person2 if rel.person1_id == person.pk else rel.person1
        rows.append(
            {
                "type": rel.get_relationship_type_display(),
                "avec": str(other),
                "lien_personne": reverse("personne-detail", args=[other.pk]),
                "date_debut": rel.start_date.isoformat() if rel.start_date else "",
                "lieu_mariage": rel.marriage_place or "",
                "date_fin": rel.end_date.isoformat() if rel.end_date else "",
            }
        )
    return rows


def _collect_comptes_geres(person: Person, viewer: Account) -> list[dict]:
    rows = []
    for owner in person.owners.all():
        rows.append(
            {
                "role": "propriétaire de ce profil",
                "personne": str(owner),
                "lien": reverse("personne-detail", args=[owner.pk]),
            }
        )
    for managed in person.managed_profiles.all():
        rows.append(
            {"role": "profil géré", "personne": str(managed), "lien": reverse("personne-detail", args=[managed.pk])}
        )
    return rows


def _collect_parametres(person: Person, viewer: Account) -> list[dict]:
    settings_obj = getattr(person, "settings", None)
    if settings_obj is None:
        return []
    return [
        {
            "notification_anniversaires": settings_obj.notify_on_birthday,
            "notification_publications": settings_obj.notify_on_new_blog_post,
            "notification_evenements": settings_obj.notify_on_event,
        }
    ]


def _collect_chalets(person: Person, viewer: Account) -> list[dict]:
    return [
        {"nom": chalet.name, "adresse": chalet.address, "lien": reverse("chalet-detail", args=[chalet.pk])}
        for chalet in person.owned_chalets.all()
    ]


def _collect_presences(person: Person, viewer: Account) -> list[dict]:
    # Unrestricted directory data -- no access helper exists or is needed
    # (any member can already see the présences calendar).
    return [
        {
            "chalet": presence.chalet.name,
            "arrivee": presence.start_date.isoformat(),
            "depart": presence.end_date.isoformat(),
        }
        for presence in person.presencepsv_set.select_related("chalet").order_by("start_date")
    ]


def _collect_publications(person: Person, viewer: Account) -> list[dict]:
    return [
        {
            "titre": post.title,
            "cree_le": post.created_at.isoformat(),
            "lien": reverse("blogpost-detail", args=[post.pk]),
        }
        for post in person.blog_posts.order_by("-created_at")
    ]


def _collect_commentaires(person: Person, viewer: Account) -> list[dict]:
    rows = []
    for comment in person.comments.select_related("post").order_by("-created_at"):
        body = comment.body
        extrait = body if len(body) <= 200 else body[:200] + "…"
        rows.append(
            {
                "extrait": extrait,
                "sur_publication": comment.post.title,
                "lien": reverse("blogpost-detail", args=[comment.post_id]),
                "cree_le": comment.created_at.isoformat(),
            }
        )
    return rows


def _collect_documents(person: Person, viewer: Account) -> list[dict]:
    from documents.access import accessible_documents

    accessible = accessible_documents(viewer)
    rows = []
    for doc in accessible.filter(uploaded_by=person).select_related("category").order_by("-created_at"):
        rows.append(
            {
                "role": "déposé par vous",
                "titre": doc.title,
                "categorie": doc.category.name,
                "lien": reverse("document-detail", args=[doc.pk]),
            }
        )
    for doc in accessible.filter(redactor=person).select_related("category").order_by("-created_at"):
        rows.append(
            {
                "role": "caviardé par vous",
                "titre": doc.title,
                "categorie": doc.category.name,
                "lien": reverse("document-detail", args=[doc.pk]),
            }
        )
    return rows


def _collect_photos(person: Person, viewer: Account) -> list[dict]:
    from photos.access import accessible_albums, accessible_photos
    from photos.models import PersonTag

    albums = accessible_albums(viewer)
    photos = accessible_photos(viewer)
    rows = []
    for album in albums.filter(created_by=person).order_by("-pk"):
        rows.append(
            {"role": "album créé par vous", "titre": album.title, "lien": reverse("album-detail", args=[album.pk])}
        )
    for photo in photos.filter(uploaded_by=person).select_related("album").order_by("-uploaded_at"):
        rows.append(
            {
                "role": "photo déposée par vous",
                "album": photo.album.title,
                "lien": reverse("photo-detail", args=[photo.pk]),
            }
        )
    for tag in PersonTag.objects.filter(person=person, photo__in=photos).select_related("photo__album"):
        rows.append(
            {
                "role": "identifié·e sur une photo",
                "album": tag.photo.album.title,
                "lien": reverse("photo-detail", args=[tag.photo_id]),
            }
        )
    for tag in PersonTag.objects.filter(tagged_by=person, photo__in=photos).select_related("photo__album", "person"):
        rows.append(
            {
                "role": "a identifié quelqu'un sur une photo",
                "personne_identifiee": str(tag.person),
                "album": tag.photo.album.title,
                "lien": reverse("photo-detail", args=[tag.photo_id]),
            }
        )
    return rows


def _collect_evenements(person: Person, viewer: Account) -> list[dict]:
    from events.access import accessible_events
    from events.models import Rsvp

    events = accessible_events(viewer)
    rows = []
    for event in events.filter(created_by=person).order_by("-start"):
        rows.append({"role": "créé par vous", "titre": event.title, "lien": reverse("event-detail", args=[event.pk])})
    for event in events.filter(organisers=person).order_by("-start"):
        rows.append(
            {"role": "organisé par vous", "titre": event.title, "lien": reverse("event-detail", args=[event.pk])}
        )
    for rsvp in Rsvp.objects.filter(person=person, event__in=events).select_related("event").order_by("-event__start"):
        rows.append(
            {
                "role": "participation",
                "titre": rsvp.event.title,
                "reponse": rsvp.get_response_display(),
                "note": rsvp.note,
                "lien": reverse("event-detail", args=[rsvp.event_id]),
            }
        )
    return rows


def _collect_genealogie(person: Person, viewer: Account) -> list[dict]:
    from genealogy.models import GedcomImport, Source, StagedIndividual, Story

    rows = []
    for story in person.stories.order_by("date"):
        rows.append(
            {
                "role": "récit vous concernant",
                "titre": story.title,
                "lien": reverse("personne-detail", args=[person.pk]) + "?tab=histoire",
            }
        )
    for story in Story.objects.filter(created_by=person).order_by("-created_at"):
        rows.append({"role": "récit rédigé par vous", "titre": story.title, "sujet": str(story.person)})
    for citation in person.citations.select_related("source").order_by("pk"):
        rows.append({"role": "citation vous concernant", "source": citation.source.title, "note": citation.note})
    for source in Source.objects.filter(created_by=person).order_by("-pk"):
        rows.append({"role": "source ajoutée par vous", "titre": source.title})
    for gedcom_import in GedcomImport.objects.filter(uploaded_by=person).order_by("-uploaded_at"):
        rows.append({"role": "import GEDCOM déposé par vous", "nom_fichier": gedcom_import.original_filename})
    for staged in StagedIndividual.objects.filter(match_person=person).select_related("gedcom_import"):
        rows.append({"role": "rapproché·e d'un import GEDCOM", "import": staged.gedcom_import.original_filename})
    for staged in StagedIndividual.objects.filter(created_person=person).select_related("gedcom_import"):
        rows.append({"role": "créé·e depuis un import GEDCOM", "import": staged.gedcom_import.original_filename})
    return rows


def _collect_consentements(person: Person, viewer: Account) -> list[dict]:
    # Consent lives on the linked Account (see annuaire/privacy_notice.py),
    # not the viewer -- an owner exporting an accountless profile's data has
    # nothing to report here, since that profile can't consent to anything.
    account = person.account
    if account is None or not account.privacy_notice_accepted_at:
        return []
    return [
        {
            "version": account.privacy_notice_version,
            "accepte_le": account.privacy_notice_accepted_at.isoformat(),
        }
    ]


PERSONAL_DATA_CATEGORIES: list[DataCategory] = [
    DataCategory("profil", _("Profil"), _("Vos informations de profil."), _collect_profil),
    DataCategory(
        "relations_familiales",
        _("Relations familiales"),
        _("Les liens familiaux enregistrés vous concernant."),
        _collect_relations_familiales,
    ),
    DataCategory(
        "comptes_geres",
        _("Comptes gérés"),
        _("Les profils que vous gérez, ou qui gèrent le vôtre."),
        _collect_comptes_geres,
    ),
    DataCategory(
        "parametres",
        _("Préférences de notification"),
        _("Vos préférences de notification."),
        _collect_parametres,
    ),
    DataCategory("chalets", _("Chalets"), _("Les chalets dont vous êtes propriétaire."), _collect_chalets),
    DataCategory("presences", _("Présences"), _("Vos séjours enregistrés dans les chalets."), _collect_presences),
    DataCategory("publications", _("Publications"), _("Les articles dont vous êtes auteur·e."), _collect_publications),
    DataCategory(
        "commentaires", _("Commentaires"), _("Les commentaires que vous avez publiés."), _collect_commentaires
    ),
    DataCategory(
        "documents",
        _("Documents"),
        _("Les documents que vous avez déposés ou caviardés, parmi ceux que vous pouvez voir."),
        _collect_documents,
    ),
    DataCategory(
        "photos",
        _("Photos"),
        _("Les albums et photos déposés, et les photos où vous êtes identifié·e, parmi ceux que vous pouvez voir."),
        _collect_photos,
    ),
    DataCategory(
        "evenements",
        _("Événements"),
        _("Les événements créés, organisés ou auxquels vous avez répondu, parmi ceux que vous pouvez voir."),
        _collect_evenements,
    ),
    DataCategory(
        "genealogie",
        _("Généalogie"),
        _("Les récits et citations généalogiques vous concernant ou rédigés par vous."),
        _collect_genealogie,
    ),
    DataCategory(
        "consentements",
        _("Consentements"),
        _("L'acceptation de la politique de confidentialité liée à votre compte."),
        _collect_consentements,
    ),
]


def collect_personal_data(person: Person, viewer: Account) -> dict[str, list[dict]]:
    return {category.key: category.collect(person, viewer) for category in PERSONAL_DATA_CATEGORIES}


def build_personal_data_archive(person: Person, viewer: Account) -> bytes:
    """Metadata + in-app links only, plus the profile photo bytes -- the one
    deliberate exception. No other file bytes (documents, photos,
    attachments) are embedded; the archive links to them instead."""
    categories_data = collect_personal_data(person, viewer)
    payload = {
        "genere_le": timezone.now().isoformat(),
        "version": 1,
        "personne": {"pk": person.pk, "prenom": person.first_name, "nom": person.last_name},
        "categories": categories_data,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("donnees.json", json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr("LISEZ-MOI.txt", _build_readme(person, categories_data))
        if person.profile_photo:
            name = person.profile_photo.name
            extension = name.rsplit(".", 1)[-1] if "." in name else "jpg"
            try:
                with person.profile_photo.open("rb") as fh:
                    archive.writestr(f"photo-profil.{extension}", fh.read())
            except (FileNotFoundError, OSError):
                pass
    return buffer.getvalue()


def _build_readme(person: Person, categories_data: dict[str, list[dict]]) -> str:
    lines = [
        _("Export des données personnelles de %(person)s — générée le %(date)s.")
        % {"person": person, "date": f"{timezone.now():%d/%m/%Y}"},
        "",
        str(
            _(
                "Ce fichier liste les métadonnées et des liens vers le contenu hébergé sur le "
                "site (voir donnees.json). Les documents, photos et pièces jointes eux-mêmes "
                "ne sont pas inclus dans cette archive ; utilisez les liens fournis pour les "
                "consulter en ligne. Votre photo de profil, elle, est incluse directement."
            )
        ),
        "",
    ]
    for category in PERSONAL_DATA_CATEGORIES:
        count = len(categories_data.get(category.key, []))
        lines.append(
            _("- %(label)s (%(count)s élément(s)) : %(note)s")
            % {"label": category.label, "count": count, "note": category.note}
        )
    return "\n".join(lines) + "\n"
