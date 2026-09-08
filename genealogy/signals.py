from annuaire.markdown_utils import markdown_to_text
from annuaire.search.indexing import register_search_index
from annuaire.search.registry import SearchSpec

from .models import Story

register_search_index(
    Story,
    SearchSpec(
        weights={"A": lambda s: s.title, "B": lambda s: markdown_to_text(s.body)},
        source_fields=frozenset({"title", "body"}),
        # No group restriction on Story (see sprint-brief.md) -- every logged-in
        # member may view any story, same posture as Person/Relation.
        accessible=lambda user: Story.objects.all(),
        label="Récits",
        card_template="genealogy/_story_search_card.html",
        order=["-date"],
    ),
)
