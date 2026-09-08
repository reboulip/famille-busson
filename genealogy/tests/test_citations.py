import pytest
from django.core.exceptions import ValidationError

from annuaire.models import Relation
from genealogy.citations import canonical_relation
from genealogy.models import Citation


@pytest.mark.django_db
def test_source_str_is_title(source):
    assert str(source) == "Acte de naissance"


@pytest.mark.django_db
def test_citation_on_story_does_not_require_claim(source, story):
    citation = Citation(source=source, story=story)
    citation.full_clean()
    citation.save()
    assert citation.claim == ""


@pytest.mark.django_db
def test_citation_on_person_requires_claim(source, person):
    citation = Citation(source=source, person=person)
    with pytest.raises(ValidationError):
        citation.full_clean()


@pytest.mark.django_db
def test_citation_on_person_with_claim_is_valid(source, person):
    citation = Citation(source=source, person=person, claim="birth_date")
    citation.full_clean()
    citation.save()
    assert citation.person == person


@pytest.mark.django_db
def test_citation_on_story_with_claim_is_invalid(source, story):
    citation = Citation(source=source, story=story, claim="birth_date")
    with pytest.raises(ValidationError):
        citation.full_clean()


@pytest.mark.django_db
def test_citation_requires_exactly_one_target(source):
    citation = Citation(source=source)
    with pytest.raises(ValidationError):
        citation.full_clean()


@pytest.mark.django_db
def test_citation_rejects_two_targets(source, story, person):
    citation = Citation(source=source, story=story, person=person, claim="birth_date")
    with pytest.raises(ValidationError):
        citation.full_clean()


@pytest.mark.django_db
def test_canonical_relation_returns_lower_person1_id_row(person, other_person):
    if person.pk < other_person.pk:
        lower, higher = person, other_person
    else:
        lower, higher = other_person, person
    relation = Relation.objects.create(person1=lower, person2=higher, relationship_type=0)
    inverse = Relation.objects.get(person1=higher, person2=lower)

    assert canonical_relation(relation) == relation
    assert canonical_relation(inverse) == relation


@pytest.mark.django_db
def test_citation_str_includes_target(source, story):
    citation = Citation.objects.create(source=source, story=story)
    assert str(source) in str(citation)
    assert str(story) in str(citation)


@pytest.mark.django_db
def test_citation_on_relation_is_stored_against_canonical_row(source, person, other_person):
    if person.pk < other_person.pk:
        lower, higher = person, other_person
    else:
        lower, higher = other_person, person
    # Create from the non-canonical side on purpose.
    non_canonical = Relation.objects.create(person1=higher, person2=lower, relationship_type=0)

    citation = Citation.objects.create(source=source, relation=non_canonical, claim="start_date")

    canonical = Relation.objects.get(person1=lower, person2=higher)
    assert citation.relation_id == canonical.pk
