import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from annuaire.models import Account
from documents.models import Document, DocumentFile

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# DocumentDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_detail_requires_login(client, document):
    response = client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_document_detail_accessible_returns_200(auth_client, document):
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_detail_404_for_document_in_restricted_category(auth_client, restricted_category):
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_document_detail_accessible_for_member_of_restricted_category(auth_client, person, restricted_category, group):
    person.account.groups.add(group)
    document = Document.objects.create(title="Doc restreint", category=restricted_category)
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_detail_shows_edit_delete_for_uploader(auth_client, person, category):
    document = Document.objects.create(title="Mon document", category=category, uploaded_by=person)
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_document_detail_shows_redactor_when_set(auth_client, person, other_person, category):
    document = Document.objects.create(
        title="Mon document", category=category, uploaded_by=person, redactor=other_person
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    assert "rédigé par" in content
    assert str(other_person) in content


@pytest.mark.django_db
def test_document_detail_hides_redactor_when_unset(auth_client, document):
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert "rédigé par" not in response.content.decode()


@pytest.mark.django_db
def test_document_detail_hides_edit_delete_for_non_uploader(auth_client, other_person, category):
    document = Document.objects.create(title="Document de Bob", category=category, uploaded_by=other_person)
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_document_detail_shows_edit_delete_for_staff(staff_client, other_person, category):
    document = Document.objects.create(title="Document de Bob", category=category, uploaded_by=other_person)
    response = staff_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_document_detail_branches_image_inline(auth_client, document):
    DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert b"<img" in response.content


@pytest.mark.django_db
def test_document_detail_single_image_has_no_carousel_strip(auth_client, document):
    DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert "document-viewer-strip" not in response.content.decode()


@pytest.mark.django_db
def test_document_detail_multi_image_shows_carousel_strip_with_every_image(auth_client, document):
    files = [
        DocumentFile.objects.create(
            document=document, file=SimpleUploadedFile(f"photo{i}.jpg", b"fake image", content_type="image/jpeg")
        )
        for i in range(3)
    ]
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    assert "document-viewer-strip" in content
    for file in files:
        assert reverse("document-file", kwargs={"pk": file.pk}) in content


@pytest.mark.django_db
def test_document_detail_multi_image_lazy_loads_all_but_the_first(auth_client, document):
    for i in range(3):
        DocumentFile.objects.create(
            document=document, file=SimpleUploadedFile(f"photo{i}.jpg", b"fake image", content_type="image/jpeg")
        )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    assert content.count('loading="lazy"') == 2


@pytest.mark.django_db
def test_document_detail_multi_image_shows_per_image_captions(auth_client, document):
    DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile("photo1.jpg", b"fake image", content_type="image/jpeg"),
        caption="Recto",
    )
    DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile("photo2.jpg", b"fake image", content_type="image/jpeg"),
        caption="Verso",
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    assert "Recto" in content
    assert "Verso" in content


@pytest.mark.django_db
def test_document_detail_images_are_zoomable(auth_client, document):
    DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert "document-viewer-zoomable" in response.content.decode()


@pytest.mark.django_db
def test_document_detail_branches_pdf_into_viewer_not_embed(auth_client, document):
    # <embed> renders nothing on many mobile browsers (no PDF plugin) -- PDFs now go
    # through a pdf.js-rendered canvas instead. See documents/static/js/document_viewer.js.
    DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    assert "<embed" not in content
    assert "document-viewer-pdf-pages" in content
    assert 'data-pdf-url="' + reverse("document-file", kwargs={"pk": document.files.get().pk}) in content


@pytest.mark.django_db
def test_document_detail_pdf_has_download_button(auth_client, document):
    doc_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    download_url = reverse("document-file", kwargs={"pk": doc_file.pk}) + "?download=1"
    assert download_url in content


@pytest.mark.django_db
def test_document_detail_viewer_has_fullscreen_button(auth_client, document):
    DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert "document-viewer-fullscreen-btn" in response.content.decode()


@pytest.mark.django_db
def test_document_detail_loads_document_viewer_js_when_file_present(auth_client, document):
    DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert "js/document_viewer.js" in response.content.decode()


@pytest.mark.django_db
def test_document_detail_omits_document_viewer_js_when_no_viewable_file(auth_client, document):
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert "js/document_viewer.js" not in response.content.decode()


@pytest.mark.django_db
def test_document_detail_branches_other_as_download_link(auth_client, document):
    doc_file = DocumentFile.objects.create(
        document=document,
        file=SimpleUploadedFile("notes.txt", b"some text", content_type="text/plain"),
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    content = response.content.decode()
    assert reverse("document-file", kwargs={"pk": doc_file.pk}) in content
    assert "download=1" in content


@pytest.mark.django_db
def test_document_detail_context_groups_files_by_preview_kind(auth_client, document):
    image_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")
    )
    pdf_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake", content_type="application/pdf")
    )
    other_file = DocumentFile.objects.create(
        document=document, file=SimpleUploadedFile("notes.txt", b"some text", content_type="text/plain")
    )
    response = auth_client.get(reverse("document-detail", kwargs={"pk": document.pk}))
    assert list(response.context["image_files"]) == [image_file]
    assert list(response.context["pdf_files"]) == [pdf_file]
    assert list(response.context["other_files"]) == [other_file]


# ---------------------------------------------------------------------------
# DocumentCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_create_requires_login(client):
    response = client.get(reverse("document-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_document_create_requires_profile(client, db):
    Account.objects.create_user(email="noprofile@example.com", password="testpass123!")
    client.login(username="noprofile@example.com", password="testpass123!")
    response = client.get(reverse("document-create"))
    assert response.status_code == 302
    assert response["Location"] == reverse("profile-create")


@pytest.mark.django_db
def test_document_create_get_returns_200(auth_client):
    response = auth_client.get(reverse("document-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_create_get_prefills_category_from_query_param(auth_client, category):
    response = auth_client.get(reverse("document-create") + f"?category={category.pk}")
    assert response.context["form"].initial.get("category") == category.pk


@pytest.mark.django_db
def test_document_create_get_ignores_non_digit_category_query_param(auth_client):
    response = auth_client.get(reverse("document-create") + "?category=abc")
    assert response.status_code == 200
    assert "category" not in response.context["form"].initial


@pytest.mark.django_db
def test_document_create_get_category_field_indents_child_under_parent(auth_client, category):
    from documents.models import Category

    child = Category.objects.create(name="Sous-catégorie", parent=category)
    response = auth_client.get(reverse("document-create"))
    choices = dict(response.context["form"].fields["category"].choices)
    assert choices[child.pk] == "    Sous-catégorie"
    assert choices[category.pk] == category.name
    assert choices[""] == "---------"


@pytest.mark.django_db
def test_document_create_category_scoped_to_accessible_for_non_staff(auth_client, category, restricted_category):
    response = auth_client.get(reverse("document-create"))
    category_qs = response.context["form"].fields["category"].queryset
    assert category in category_qs
    assert restricted_category not in category_qs


@pytest.mark.django_db
def test_document_create_shows_all_categories_for_staff(auth_client, person, restricted_category):
    person.account.is_staff = True
    person.account.save()
    response = auth_client.get(reverse("document-create"))
    category_qs = response.context["form"].fields["category"].queryset
    assert restricted_category in category_qs


def _formset_management_data(prefix="files", total=0):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.mark.django_db
def test_document_create_post_creates_document_and_sets_uploaded_by(auth_client, person, category, document_post_data):
    data = document_post_data(category, title="Acte de vente")
    response = auth_client.post(reverse("document-create"), data)
    assert response.status_code == 302
    document = Document.objects.get(title="Acte de vente")
    assert document.uploaded_by == person


@pytest.mark.django_db
def test_document_create_post_with_file_creates_document_file(auth_client, category, document_post_data):
    data = document_post_data(category, title="Avec fichier")
    response = auth_client.post(reverse("document-create"), data)
    assert response.status_code == 302
    document = Document.objects.get(title="Avec fichier")
    assert document.files.count() == 1


@pytest.mark.django_db
def test_document_create_post_with_zero_files_shows_error_and_creates_nothing(
    auth_client, category, document_post_data
):
    data = document_post_data(category, title="Sans fichier", files=0)
    response = auth_client.post(reverse("document-create"), data)
    assert response.status_code == 200
    assert "Un document doit contenir au moins un fichier." in response.content.decode()
    assert not Document.objects.filter(title="Sans fichier").exists()


@pytest.mark.django_db
def test_document_create_post_sets_redactor(auth_client, category, other_person, document_post_data):
    data = document_post_data(category, title="Avec rédacteur", redactor=other_person.pk)
    response = auth_client.post(reverse("document-create"), data)
    assert response.status_code == 302
    document = Document.objects.get(title="Avec rédacteur")
    assert document.redactor == other_person


@pytest.mark.django_db
def test_document_create_get_person_picker_loads_js(auth_client):
    response = auth_client.get(reverse("document-create"))
    assert "js/person_picker.js" in response.content.decode()


@pytest.mark.django_db
def test_document_create_get_loads_markdown_editor_widget(auth_client):
    response = auth_client.get(reverse("document-create"))
    content = response.content.decode()
    assert "js/markdown_editor.js" in content
    assert "markdown-editor-toolbar" in content


@pytest.mark.django_db
def test_document_create_get_redactor_initial_json_empty_by_default(auth_client):
    response = auth_client.get(reverse("document-create"))
    assert response.context["redactor_initial_json"] == "[]"


# ---------------------------------------------------------------------------
# DocumentUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_update_requires_login(client, document):
    response = client.get(reverse("document-edit", kwargs={"pk": document.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_document_update_forbidden_for_non_uploader(auth_client, other_person, category):
    document = Document.objects.create(title="Document de Bob", category=category, uploaded_by=other_person)
    response = auth_client.get(reverse("document-edit", kwargs={"pk": document.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_document_update_allowed_for_uploader(auth_client, person, category):
    document = Document.objects.create(title="Mon document", category=category, uploaded_by=person)
    response = auth_client.get(reverse("document-edit", kwargs={"pk": document.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_update_allowed_for_staff(staff_client, other_person, category):
    document = Document.objects.create(title="Document de Bob", category=category, uploaded_by=other_person)
    response = staff_client.get(reverse("document-edit", kwargs={"pk": document.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_update_get_redactor_initial_json_prefills_existing_redactor(
    auth_client, person, other_person, category
):
    document = Document.objects.create(
        title="Mon document", category=category, uploaded_by=person, redactor=other_person
    )
    response = auth_client.get(reverse("document-edit", kwargs={"pk": document.pk}))
    assert f'"id": {other_person.pk}' in response.context["redactor_initial_json"]


@pytest.mark.django_db
def test_document_update_post_changes_redactor(auth_client, person, other_person, category, document_post_data):
    document = Document.objects.create(title="Mon document", category=category, uploaded_by=person)
    data = document_post_data(category, title="Mon document", redactor=other_person.pk)
    response = auth_client.post(reverse("document-edit", kwargs={"pk": document.pk}), data)
    assert response.status_code == 302
    document.refresh_from_db()
    assert document.redactor == other_person


@pytest.mark.django_db
def test_document_update_renders_with_existing_file(auth_client, person, category):
    """The formset's file widget must never call FieldFile.url() -- DocumentStorage.url()
    always raises since protected files have no public URL, which crashed this exact
    page with a 500 before documents/widgets.py's DocumentFileInput was introduced."""
    document = Document.objects.create(title="Mon document", category=category, uploaded_by=person)
    DocumentFile.objects.create(document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake"))
    response = auth_client.get(reverse("document-edit", kwargs={"pk": document.pk}))
    assert response.status_code == 200
    assert b"scan.pdf" in response.content


@pytest.mark.django_db
def test_document_update_post_renames_document(auth_client, person, category, document_post_data):
    document = Document.objects.create(title="Ancien titre", category=category, uploaded_by=person)
    data = document_post_data(category, title="Nouveau titre")
    response = auth_client.post(reverse("document-edit", kwargs={"pk": document.pk}), data)
    assert response.status_code == 302
    document.refresh_from_db()
    assert document.title == "Nouveau titre"


@pytest.mark.django_db
def test_document_update_post_with_zero_files_shows_error_and_does_not_save(
    auth_client, person, category, document_post_data
):
    document = Document.objects.create(title="Ancien titre", category=category, uploaded_by=person)
    data = document_post_data(category, title="Nouveau titre", files=0)
    response = auth_client.post(reverse("document-edit", kwargs={"pk": document.pk}), data)
    assert response.status_code == 200
    assert "Un document doit contenir au moins un fichier." in response.content.decode()
    document.refresh_from_db()
    assert document.title == "Ancien titre"


@pytest.mark.django_db
def test_document_update_post_deleting_the_only_file_shows_error(auth_client, person, category):
    document = Document.objects.create(title="Mon document", category=category, uploaded_by=person)
    doc_file = DocumentFile.objects.create(document=document, file=SimpleUploadedFile("scan.pdf", b"%PDF-fake"))
    data = {"title": "Mon document", "category": category.pk, "document_date": "", "description": ""}
    data.update(_formset_management_data(total=1))
    data["files-INITIAL_FORMS"] = "1"
    data["files-0-id"] = str(doc_file.pk)
    data["files-0-caption"] = ""
    data["files-0-DELETE"] = "on"
    response = auth_client.post(reverse("document-edit", kwargs={"pk": document.pk}), data)
    assert response.status_code == 200
    assert "Un document doit contenir au moins un fichier." in response.content.decode()
    assert DocumentFile.objects.filter(pk=doc_file.pk).exists()


# ---------------------------------------------------------------------------
# DocumentDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_delete_forbidden_for_non_uploader(auth_client, other_person, category):
    document = Document.objects.create(title="Document de Bob", category=category, uploaded_by=other_person)
    response = auth_client.get(reverse("document-delete", kwargs={"pk": document.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_document_delete_post_removes_document(auth_client, person, category):
    document = Document.objects.create(title="À supprimer", category=category, uploaded_by=person)
    response = auth_client.post(reverse("document-delete", kwargs={"pk": document.pk}))
    assert response.status_code == 302
    assert not Document.objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_document_delete_post_allowed_for_staff(staff_client, other_person, category):
    document = Document.objects.create(title="Document de Bob", category=category, uploaded_by=other_person)
    response = staff_client.post(reverse("document-delete", kwargs={"pk": document.pk}))
    assert response.status_code == 302
    assert not Document.objects.filter(pk=document.pk).exists()
