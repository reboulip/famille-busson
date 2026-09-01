import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.forms import DocumentFileFormSet


def _management_data(prefix="files", total=0, initial=0):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.mark.django_db
def test_document_file_formset_requires_at_least_one_file(document):
    data = _management_data(total=0)
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert not formset.is_valid()
    assert "Un document doit contenir au moins un fichier." in formset.non_form_errors()


@pytest.mark.django_db
def test_document_file_formset_valid_with_one_file(document):
    uploaded = SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    data = _management_data(total=1)
    data["files-0-caption"] = ""
    formset = DocumentFileFormSet(data, {"files-0-file": uploaded}, instance=document)
    assert formset.is_valid()


@pytest.mark.django_db
def test_document_file_formset_rejects_a_row_with_only_a_caption(document):
    # A caption with no file is invalid too, but via the row's own required-field
    # error rather than the formset-level message -- that field error already says
    # exactly what's wrong, so clean() skips piling on the generic one.
    data = _management_data(total=1)
    data["files-0-caption"] = "Une légende sans fichier"
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert not formset.is_valid()
    assert formset.forms[0].errors.get("file")


@pytest.mark.django_db
def test_document_file_formset_deleting_the_only_file_is_invalid(document, document_file):
    data = _management_data(total=1, initial=1)
    data["files-0-id"] = str(document_file.pk)
    data["files-0-caption"] = document_file.caption
    data["files-0-DELETE"] = "on"
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert not formset.is_valid()
    assert "Un document doit contenir au moins un fichier." in formset.non_form_errors()


@pytest.mark.django_db
def test_document_file_formset_deleting_one_of_two_files_is_valid(document, document_file):
    second = document.files.create(file=SimpleUploadedFile("second.pdf", b"%PDF-fake"))
    data = _management_data(total=2, initial=2)
    data["files-0-id"] = str(document_file.pk)
    data["files-0-caption"] = document_file.caption
    data["files-0-DELETE"] = "on"
    data["files-1-id"] = str(second.pk)
    data["files-1-caption"] = ""
    formset = DocumentFileFormSet(data, {}, instance=document)
    assert formset.is_valid()
