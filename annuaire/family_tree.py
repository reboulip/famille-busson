"""Serialize Person/Relation records into the family-chart JS library's data format.

See docs/data_model.md for the Relation model. relationship_type=2 on a row means
"person2 is a parent of person1" (and 3 the inverse, "child"); 0 (mariage) and 1
(conjoint) both mean "spouse" and collapse into a single rels.spouses list here --
the mariage/conjoint distinction is a display-only nuance the tree doesn't need.
"""

from __future__ import annotations

from django.templatetags.static import static
from django.urls import reverse

from .models import Person, Relation

_PARENT = 2
_CHILD = 3
_SPOUSE_TYPES = (0, 1)


def build_family_chart_data() -> list[dict]:
    """One dict per Person, in family-chart's {id, data, rels} shape. rels lists
    are built from both directions of every Relation row (the post_save signal
    keeps both sides in sync -- see CLAUDE.md), then defensively symmetrized in
    case a row was written outside that signal (bulk_create, fixtures)."""
    nodes: dict[int, dict] = {
        person.pk: {
            "id": str(person.pk),
            "data": {
                "gender": person.gender or "",
                "first name": person.first_name,
                "last name": person.last_name,
                "birthday": str(person.birth_date.year) if person.birth_date else "",
                "avatar": person.profile_photo.url if person.profile_photo else static("default_profile_picture.png"),
                "url": reverse("personne-detail", kwargs={"pk": person.pk}),
            },
            "rels": {"parents": [], "spouses": [], "children": []},
        }
        for person in Person.objects.all()
    }

    for rel in Relation.objects.all():
        if rel.person1_id == rel.person2_id or rel.person1_id not in nodes or rel.person2_id not in nodes:
            continue
        rels = nodes[rel.person1_id]["rels"]
        target_id = str(rel.person2_id)
        if rel.relationship_type == _PARENT and target_id not in rels["parents"]:
            rels["parents"].append(target_id)
        elif rel.relationship_type == _CHILD and target_id not in rels["children"]:
            rels["children"].append(target_id)
        elif rel.relationship_type in _SPOUSE_TYPES and target_id not in rels["spouses"]:
            rels["spouses"].append(target_id)

    _symmetrize(nodes)
    return list(nodes.values())


def _symmetrize(nodes: dict[int, dict]) -> None:
    """Mirror any one-sided link so both ends agree, without trusting that every
    Relation row went through the post_save signal that normally guarantees it."""
    for pk, node in nodes.items():
        pk_str = str(pk)
        for parent_id in node["rels"]["parents"]:
            parent_node = nodes.get(int(parent_id))
            if parent_node and pk_str not in parent_node["rels"]["children"]:
                parent_node["rels"]["children"].append(pk_str)
        for child_id in node["rels"]["children"]:
            child_node = nodes.get(int(child_id))
            if child_node and pk_str not in child_node["rels"]["parents"]:
                child_node["rels"]["parents"].append(pk_str)
        for spouse_id in node["rels"]["spouses"]:
            spouse_node = nodes.get(int(spouse_id))
            if spouse_node and pk_str not in spouse_node["rels"]["spouses"]:
                spouse_node["rels"]["spouses"].append(pk_str)


def find_components(data: list[dict]) -> list[dict]:
    """Group nodes into connected components via their rels links. One entry per
    component -- {"root_id", "size", "label"} -- sorted largest first. The
    suggested root/anchor is the member with the most relations, tie-broken by
    earliest birthday then by id, so it's deterministic."""
    by_id = {node["id"]: node for node in data}
    parent = dict.fromkeys(by_id, None)
    for node_id in by_id:
        parent[node_id] = node_id

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b

    for node in data:
        for other_id in node["rels"]["parents"] + node["rels"]["spouses"] + node["rels"]["children"]:
            union(node["id"], other_id)

    groups: dict[str, list[str]] = {}
    for node_id in by_id:
        groups.setdefault(find(node_id), []).append(node_id)

    def degree(node_id: str) -> int:
        rels = by_id[node_id]["rels"]
        return len(rels["parents"]) + len(rels["spouses"]) + len(rels["children"])

    def birth_sort_key(node_id: str) -> tuple[bool, str]:
        birthday = by_id[node_id]["data"]["birthday"]
        return (birthday == "", birthday)

    components = []
    for member_ids in groups.values():
        root_id = min(member_ids, key=lambda nid: (-degree(nid), birth_sort_key(nid), int(nid)))
        root_data = by_id[root_id]["data"]
        components.append(
            {
                "root_id": root_id,
                "size": len(member_ids),
                "label": f"{root_data['first name']} {root_data['last name']}",
            }
        )

    components.sort(key=lambda component: -component["size"])
    return components
