"""Detect likely-duplicate Person rows and merge them safely.

Merging is not a single generic reflection loop over Person._meta: several
relations need bespoke handling (a unique-together constraint on the far side,
the self-referential owners M2M, the account link, the profile photo file, and
Relation's own inverse-mirroring signal all behave differently under a blind
FK repoint). Instead, every relation is handled explicitly below, and
`test_person_meta_guard_covers_every_relation` (annuaire/tests/test_person_merge.py)
is the actual safety net: it walks Person._meta.get_fields(include_hidden=True)
and fails if a new FK/M2M onto Person is ever added without a matching entry in
HANDLED_RELATIONS/HANDLED_HIDDEN_RELATIONS, so a future model change can't
silently escape the merge.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import Person, Relation
from .search.indexing import enqueue_reindex
from .search.text import normalize

# Every visible reverse accessor name this module knows how to migrate off a
# merged-away Person, plus the two forward M2M field names. Checked by the
# meta-guard test below.
HANDLED_RELATIONS: set[str] = {
    "owners",  # forward self-M2M
    "managed_profiles",  # reverse of owners
    "settings",  # O2O CASCADE -- left to cascade-delete with the loser
    "ascending_relations",  # Relation.person1
    "descending_relations",  # Relation.person2
    "owned_chalets",  # Chalet.owners M2M
    "presencepsv_set",  # PresencePSV.person
    "blog_posts",  # BlogPost.authors M2M
    "comments",  # Comment.author
    "documents",  # Document.uploaded_by
    "redacted_documents",  # Document.redactor
    "created_albums",  # Album.created_by
    "uploaded_photos",  # Photo.uploaded_by
    "tagged_photos",  # PersonTag.person
    "created_events",  # Event.created_by
    "organised_events",  # Event.organisers M2M
    "rsvps",  # Rsvp.person
    "stories",  # genealogy.Story.person
    "citations",  # genealogy.Citation.person
}

# Hidden relations (related_name="+") have no accessor name, so they're tracked
# by (app_label, model_name, field_name) instead.
HANDLED_HIDDEN_RELATIONS: set[tuple[str, str, str]] = {
    ("photos", "persontag", "tagged_by"),
    ("genealogy", "story", "created_by"),
    ("genealogy", "source", "created_by"),
}

# Reverse-M2M accessor -> the field name on the related model that actually
# holds the M2M (used to .add(winner) on each of the loser's related rows).
_M2M_REVERSE_FIELD = {
    "blog_posts": "authors",
    "owned_chalets": "owners",
    "organised_events": "organisers",
}

# Simple (model, field_name) FK repoints: no unique-together constraint on the
# far side, so a blind bulk .update() is safe.
_SIMPLE_REPOINTS: list[tuple[str, str]] = [
    ("annuaire", "presencepsv", "person"),
    ("publications", "comment", "author"),
    ("documents", "document", "uploaded_by"),
    ("documents", "document", "redactor"),
    ("photos", "album", "created_by"),
    ("photos", "photo", "uploaded_by"),
    ("photos", "persontag", "tagged_by"),
    ("events", "event", "created_by"),
    ("genealogy", "story", "person"),
    ("genealogy", "story", "created_by"),
    ("genealogy", "source", "created_by"),
    ("genealogy", "citation", "person"),
]

# Scalar Person fields a merge may need to reconcile when they differ between
# winner and loser. account/profile_photo are handled separately (special rules).
MERGE_SCALAR_FIELDS = [
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "postal_address",
    "latitude",
    "longitude",
    "birth_date",
    "birth_place",
    "deceased",
    "death_date",
    "death_place",
    "description",
    "profile_photo",
]


@dataclass(frozen=True)
class DuplicateCandidate:
    person1_id: int
    person2_id: int
    reason: str


@dataclass
class MergeReport:
    moved_counts: dict[str, int] = field(default_factory=dict)
    dropped: list[str] = field(default_factory=list)


def find_duplicate_candidates(*, limit: int = 200) -> list[DuplicateCandidate]:
    """Cheap, deterministic candidate detection -- computed live, never persisted
    (keeps this item out of any migration-numbering race, and a same-surname
    family will simply see the same near-matches again on every call, which is
    an accepted v1 limitation -- see sprint-brief.md)."""
    people = list(Person.objects.all())
    pairs: dict[frozenset[int], str] = {}

    by_name: dict[tuple[str, str], list[Person]] = {}
    by_lastname_birth: dict[tuple[str, object], list[Person]] = {}
    by_email: dict[str, list[Person]] = {}
    for p in people:
        by_name.setdefault((normalize(p.last_name), normalize(p.first_name)), []).append(p)
        if p.birth_date:
            by_lastname_birth.setdefault((normalize(p.last_name), p.birth_date), []).append(p)
        if p.email:
            by_email.setdefault(normalize(p.email), []).append(p)

    def _pairs_from(groups: dict, reason: str) -> None:
        for members in groups.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    pair = frozenset({members[i].pk, members[j].pk})
                    pairs.setdefault(pair, reason)

    _pairs_from(by_name, "Nom et prénom identiques")
    _pairs_from(by_lastname_birth, "Même nom et même date de naissance")
    _pairs_from(by_email, "Adresse email identique")

    by_pk = {p.pk: p for p in people}
    candidates = [
        DuplicateCandidate(person1_id=min(pair), person2_id=max(pair), reason=reason) for pair, reason in pairs.items()
    ]
    candidates.sort(
        key=lambda c: (by_pk[c.person1_id].last_name, by_pk[c.person1_id].first_name, c.person1_id, c.person2_id)
    )
    return candidates[:limit]


def merge_persons(winner: Person, loser: Person, *, field_choices: dict[str, int] | None = None) -> MergeReport:
    """Merge `loser` into `winner`. `field_choices` maps a differing scalar field
    name to 1 (keep winner's value) or 2 (take loser's value); any field not
    listed defaults to the winner's value if non-blank, else the loser's."""
    if winner.pk == loser.pk:
        raise ValidationError("Impossible de fusionner une personne avec elle-même.")
    if winner.account_id is not None and loser.account_id is not None:
        raise ValidationError("Ces deux profils ont chacun un compte lié à un utilisateur ; la fusion est refusée.")

    field_choices = field_choices or {}
    report = MergeReport()

    with transaction.atomic():
        _reconcile_scalar_fields(winner, loser, field_choices)
        winner.save()

        if loser.account_id is not None:
            account = loser.account
            loser.account = None
            loser.save(update_fields=["account"])
            winner.account = account
            winner.save(update_fields=["account"])
            report.moved_counts["account"] = 1

        _merge_relations(winner, loser, report)
        _merge_owners(winner, loser, report)

        for app_label, model_name, field_name in _SIMPLE_REPOINTS:
            _repoint(app_label, model_name, field_name, winner, loser, report)

        _merge_person_tags(winner, loser, report)
        _merge_rsvps(winner, loser, report)

        for accessor in _M2M_REVERSE_FIELD:
            _merge_m2m(winner, loser, accessor, report)

        loser_label = str(loser)
        loser.delete()
        report.dropped.append(loser_label)

    enqueue_reindex(Person, winner.pk)
    return report


def _reconcile_scalar_fields(winner: Person, loser: Person, field_choices: dict[str, int]) -> None:
    for field_name in MERGE_SCALAR_FIELDS:
        winner_value = getattr(winner, field_name)
        loser_value = getattr(loser, field_name)
        choice = field_choices.get(field_name)
        if choice == 2:
            setattr(winner, field_name, loser_value)
        elif choice == 1:
            continue
        elif not winner_value and loser_value:
            setattr(winner, field_name, loser_value)


def _repoint(
    app_label: str, model_name: str, field_name: str, winner: Person, loser: Person, report: MergeReport
) -> None:
    model = apps.get_model(app_label, model_name)
    qs = model.objects.filter(**{field_name: loser})
    count = qs.count()
    if count:
        qs.update(**{field_name: winner})
        report.moved_counts[f"{app_label}.{model_name}.{field_name}"] = count


def _merge_owners(winner: Person, loser: Person, report: MergeReport) -> None:
    owners_of_loser = list(loser.owners.all())
    managed_by_loser = list(loser.managed_profiles.all())
    for owner in owners_of_loser:
        winner.owners.add(owner)
    for managed in managed_by_loser:
        managed.owners.add(winner)
    winner.owners.remove(winner)
    total = len(owners_of_loser) + len(managed_by_loser)
    if total:
        report.moved_counts["owners"] = total


def _merge_m2m(winner: Person, loser: Person, accessor: str, report: MergeReport) -> None:
    field_name = _M2M_REVERSE_FIELD[accessor]
    related_objs = list(getattr(loser, accessor).all())
    for obj in related_objs:
        getattr(obj, field_name).add(winner)
    if related_objs:
        report.moved_counts[accessor] = len(related_objs)


def _merge_person_tags(winner: Person, loser: Person, report: MergeReport) -> None:
    from photos.models import PersonTag

    tags = list(PersonTag.objects.filter(person=loser).select_related("photo"))
    moved = 0
    for tag in tags:
        if PersonTag.objects.filter(photo_id=tag.photo_id, person=winner).exists():
            tag.delete()
        else:
            tag.person = winner
            tag.save(update_fields=["person"])
            moved += 1
    if tags:
        report.moved_counts["photos.PersonTag"] = moved


def _merge_rsvps(winner: Person, loser: Person, report: MergeReport) -> None:
    from events.models import Rsvp

    rsvps = list(Rsvp.objects.filter(person=loser))
    moved = 0
    for rsvp in rsvps:
        if Rsvp.objects.filter(event_id=rsvp.event_id, person=winner).exists():
            rsvp.delete()
        else:
            rsvp.person = winner
            rsvp.save(update_fields=["person"])
            moved += 1
    if rsvps:
        report.moved_counts["events.Rsvp"] = moved


def _merge_relations(winner: Person, loser: Person, report: MergeReport) -> None:
    loser_relations = list(Relation.objects.filter(Q(person1=loser) | Q(person2=loser)))
    by_other: dict[int, list[Relation]] = {}
    for rel in loser_relations:
        other_id = rel.person2_id if rel.person1_id == loser.pk else rel.person1_id
        by_other.setdefault(other_id, []).append(rel)

    winner_other_ids: set[int] = set()
    for p1, p2 in Relation.objects.filter(Q(person1=winner) | Q(person2=winner)).values_list(
        "person1_id", "person2_id"
    ):
        winner_other_ids.add(p2 if p1 == winner.pk else p1)

    to_recreate: list[dict] = []
    for other_id, rels in by_other.items():
        # loser<->winner edge: drop rather than recreate as a self-relation --
        # e.g. merging two people who are already parent and child.
        if other_id == winner.pk:
            continue
        if other_id in winner_other_ids:
            continue
        # Prefer the row where loser is person1, so the remap preserves the
        # exact relationship_type loser held from their own side; the signal
        # regenerates the mirror on the other side automatically.
        rel = next((r for r in rels if r.person1_id == loser.pk), rels[0])
        person1_id = winner.pk if rel.person1_id == loser.pk else rel.person1_id
        person2_id = winner.pk if rel.person2_id == loser.pk else rel.person2_id
        to_recreate.append(
            {
                "person1_id": person1_id,
                "person2_id": person2_id,
                "relationship_type": rel.relationship_type,
                "start_date": rel.start_date,
                "marriage_place": rel.marriage_place,
                "end_date": rel.end_date,
            }
        )

    Relation.objects.filter(pk__in=[r.pk for r in loser_relations]).delete()
    for kwargs in to_recreate:
        Relation.objects.create(**kwargs)

    if loser_relations:
        report.moved_counts["annuaire.Relation"] = len(to_recreate)
