import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from documents.models import Document, DocumentFile

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_document_file_requires_login(client, document_file):
    response = client.get(reverse("document-file", kwargs={"pk": document_file.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_document_file_accessible_returns_200(auth_client, document_file):
    response = auth_client.get(reverse("document-file", kwargs={"pk": document_file.pk}))
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"%PDF-fake"


@pytest.mark.django_db
def test_document_file_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("document-file", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_document_file_non_member_of_restricted_category_forbidden(auth_client, restricted_category):
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    doc_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    )
    response = auth_client.get(reverse("document-file", kwargs={"pk": doc_file.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_document_file_member_of_restricted_category_allowed(auth_client, person, restricted_category, group):
    person.account.groups.add(group)
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    doc_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    )
    response = auth_client.get(reverse("document-file", kwargs={"pk": doc_file.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_file_staff_bypasses_restriction(staff_client, restricted_category):
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    doc_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    )
    response = staff_client.get(reverse("document-file", kwargs={"pk": doc_file.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_file_pdf_is_inline(auth_client, document_file):
    response = auth_client.get(reverse("document-file", kwargs={"pk": document_file.pk}))
    assert response["Content-Disposition"].startswith("inline")


@pytest.mark.django_db
def test_document_file_docx_is_attachment(auth_client, document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile(
            "letter.docx", b"fake docx", content_type="application/vnd.openxmlformats-officedocument"
        ),
    )
    response = auth_client.get(reverse("document-file", kwargs={"pk": doc_file.pk}))
    assert response["Content-Disposition"].startswith("attachment")


@pytest.mark.django_db
def test_document_file_download_param_forces_attachment_for_pdf(auth_client, document_file):
    response = auth_client.get(reverse("document-file", kwargs={"pk": document_file.pk}), {"download": "1"})
    assert response["Content-Disposition"].startswith("attachment")


@pytest.mark.django_db
def test_document_file_sets_nosniff_header(auth_client, document_file):
    response = auth_client.get(reverse("document-file", kwargs={"pk": document_file.pk}))
    assert response["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
def test_document_file_sets_xframe_options_sameorigin(auth_client, document_file):
    response = auth_client.get(reverse("document-file", kwargs={"pk": document_file.pk}))
    assert response["X-Frame-Options"] == "SAMEORIGIN"


@pytest.mark.django_db
def test_document_file_content_type_for_pdf(auth_client, document_file):
    response = auth_client.get(reverse("document-file", kwargs={"pk": document_file.pk}))
    assert response["Content-Type"] == "application/pdf"


# ---------------------------------------------------------------------------
# Thumbnail variant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_file_thumbnail_missing_returns_404(auth_client, document_file):
    response = auth_client.get(reverse("document-file-thumbnail", kwargs={"pk": document_file.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_document_file_thumbnail_present_returns_200(auth_client, document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf"),
        thumbnail=SimpleUploadedFile("thumb.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png"),
    )
    response = auth_client.get(reverse("document-file-thumbnail", kwargs={"pk": doc_file.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_file_thumbnail_requires_access(auth_client, restricted_category):
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    doc_file = DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf"),
        thumbnail=SimpleUploadedFile("thumb.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png"),
    )
    response = auth_client.get(reverse("document-file-thumbnail", kwargs={"pk": doc_file.pk}))
    assert response.status_code == 403
