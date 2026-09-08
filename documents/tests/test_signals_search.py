"""11.2 -- Document's signal-driven search reindexing, including the
DocumentFile deletion leak fix (a deleted scan's OCR text must not stay
searchable on the parent Document -- an access-control-adjacent leak)."""

import pytest

from documents.models import Document


@pytest.mark.django_db
def test_creating_a_document_populates_search_text(category, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        document = Document.objects.create(title="Été à Genève", category=category, description="**gras**")

    document.refresh_from_db()
    assert "ete" in document.search_text
    assert "geneve" in document.search_text
    assert "gras" in document.search_text


@pytest.mark.django_db
def test_document_file_extracted_text_is_folded_into_parent_index(
    document, document_file, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        document_file.extracted_text = "contenu numerise unique"
        document_file.save()

    document.refresh_from_db()
    assert "numerise" in document.search_text


@pytest.mark.django_db
def test_deleting_a_document_file_removes_its_text_from_the_parent_index(
    document, document_file, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        document_file.extracted_text = "contenu numerise unique"
        document_file.save()
    document.refresh_from_db()
    assert "numerise" in document.search_text

    with django_capture_on_commit_callbacks(execute=True):
        document_file.delete()

    document.refresh_from_db()
    assert "numerise" not in document.search_text
