from annuaire.models import Relation


def canonical_relation(relation: Relation) -> Relation:
    """The canonical row of a mirrored Relation pair -- the one whose person1_id
    is numerically lower. A citation always targets this row: create_inverse_relation
    / delete_inverse_relation (annuaire/signals.py) keep both mirrored rows in sync
    for their own fields, but a citation attached to the non-canonical row would
    vanish the moment that specific row is deleted and recreated (e.g. a relation
    edited from the other person's screen)."""
    if relation.person1_id < relation.person2_id:
        return relation
    if relation.person1_id > relation.person2_id:
        return Relation.objects.get(person1_id=relation.person2_id, person2_id=relation.person1_id)
    return relation
