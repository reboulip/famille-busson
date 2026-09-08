from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.db.models import Model, QuerySet

_registry: dict[type[Model], "SearchSpec"] = {}


@dataclass(frozen=True)
class SearchSpec:
    """Declares how one model participates in global search.

    `accessible` has no default on purpose: a model registered without an explicit
    access rule would silently fall back to searching every row, leaking restricted
    content the first time someone typed a matching query.
    """

    weights: dict[str, Callable[[Any], str]]
    source_fields: frozenset[str]
    accessible: Callable[[Any], QuerySet]
    label: str
    card_template: str
    order: list[str] = field(default_factory=list)


def register(model: type[Model], spec: SearchSpec) -> None:
    _registry[model] = spec


def get_spec(model: type[Model]) -> SearchSpec:
    return _registry[model]


def all_specs() -> dict[type[Model], SearchSpec]:
    return dict(_registry)
