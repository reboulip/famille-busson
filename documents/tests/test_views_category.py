import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from documents.models import Category, Document

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# CategoryListView -- "visible but locked"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_list_requires_login(client):
    response = client.get(reverse("category-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_category_list_shows_public_category(auth_client, category):
    response = auth_client.get(reverse("category-list"))
    assert category.name in response.content.decode()


@pytest.mark.django_db
def test_category_list_shows_restricted_category_name_for_non_member(auth_client, restricted_category):
    response = auth_client.get(reverse("category-list"))
    content = response.content.decode()
    assert restricted_category.name in content
    # The 🔒 emoji became an inline SVG glyph in the Alpenglow design pass (emoji
    # renders as a tofu box wherever the system has no emoji font). The locked state
    # is still carried three ways: the glyph, the muted name, and the words below.
    assert "category-tree__name--locked" in content
    assert "Réservé au groupe" in content


@pytest.mark.django_db
def test_category_list_does_not_link_locked_category_for_non_member(auth_client, restricted_category):
    response = auth_client.get(reverse("category-list"))
    detail_url = reverse("category-detail", kwargs={"pk": restricted_category.pk})
    assert f'href="{detail_url}"' not in response.content.decode()


@pytest.mark.django_db
def test_category_list_links_restricted_category_for_member(auth_client, person, restricted_category, group):
    person.account.groups.add(group)
    response = auth_client.get(reverse("category-list"))
    detail_url = reverse("category-detail", kwargs={"pk": restricted_category.pk})
    assert f'href="{detail_url}"' in response.content.decode()


@pytest.mark.django_db
def test_category_list_shows_all_categories_for_staff(staff_client, restricted_category):
    response = staff_client.get(reverse("category-list"))
    detail_url = reverse("category-detail", kwargs={"pk": restricted_category.pk})
    assert f'href="{detail_url}"' in response.content.decode()


@pytest.mark.django_db
def test_category_list_shows_markdown_plain_excerpt_for_accessible_category(auth_client, category):
    category.description = "**gras** et [lien](https://example.com)"
    category.save()
    response = auth_client.get(reverse("category-list"))
    content = response.content.decode()
    assert "gras" in content
    assert "<strong>" not in content
    assert "[lien]" not in content


@pytest.mark.django_db
def test_category_list_hides_excerpt_for_locked_category(auth_client, restricted_category):
    restricted_category.description = "Contenu secret"
    restricted_category.save()
    response = auth_client.get(reverse("category-list"))
    assert "Contenu secret" not in response.content.decode()


# ---------------------------------------------------------------------------
# CategoryDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_detail_requires_login(client, category):
    response = client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_category_detail_accessible_shows_description(auth_client, category):
    category.description = "**Important**"
    category.save()
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    assert response.status_code == 200
    assert "<strong>Important</strong>" in response.content.decode()


@pytest.mark.django_db
def test_category_detail_locked_for_non_member_shows_placeholder_not_content(auth_client, restricted_category):
    restricted_category.description = "Contenu secret"
    restricted_category.save()
    response = auth_client.get(reverse("category-detail", kwargs={"pk": restricted_category.pk}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Contenu secret" not in content
    assert "réservée" in content


@pytest.mark.django_db
def test_category_detail_locked_resolves_normally_not_403_or_404(auth_client, restricted_category):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": restricted_category.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_category_detail_shows_only_accessible_documents(auth_client, category, restricted_category):
    Document.objects.create(title="Doc public", category=category)
    Document.objects.create(title="Doc restreint", category=restricted_category)
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    content = response.content.decode()
    assert "Doc public" in content


@pytest.mark.django_db
def test_category_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_category_detail_shows_add_document_button_linking_to_create_with_category(auth_client, category):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    content = response.content.decode()
    expected_url = reverse("document-create") + f"?category={category.pk}"
    assert expected_url in content


@pytest.mark.django_db
def test_category_detail_locked_hides_add_document_button(auth_client, restricted_category):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": restricted_category.pk}))
    content = response.content.decode()
    assert "Ajouter un document" not in content


@pytest.mark.django_db
def test_category_detail_shows_tous_for_unrestricted_category(auth_client, category):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    assert response.context["access_groups"] == []
    assert "Visible par" in response.content.decode()
    assert "Tous" in response.content.decode()


@pytest.mark.django_db
def test_category_detail_shows_group_names_for_restricted_category(auth_client, restricted_category, group):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": restricted_category.pk}))
    assert list(response.context["access_groups"]) == [group]
    assert group.name in response.content.decode()


@pytest.mark.django_db
def test_category_detail_locked_alert_still_says_reservee(auth_client, restricted_category):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": restricted_category.pk}))
    assert "réservée" in response.content.decode()


@pytest.mark.django_db
def test_category_detail_has_no_ancestors_for_root_category(auth_client, category):
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    assert response.context["ancestors"] == []


@pytest.mark.django_db
def test_category_detail_shows_parent_link(auth_client, category):
    child = Category.objects.create(name="Enfant", parent=category)
    response = auth_client.get(reverse("category-detail", kwargs={"pk": child.pk}))
    assert response.context["ancestors"] == [category]
    parent_url = reverse("category-detail", kwargs={"pk": category.pk})
    assert f'href="{parent_url}"' in response.content.decode()


@pytest.mark.django_db
def test_category_detail_shows_grandparent_then_parent_in_order(auth_client, category):
    parent = Category.objects.create(name="Parent", parent=category)
    child = Category.objects.create(name="Enfant", parent=parent)
    response = auth_client.get(reverse("category-detail", kwargs={"pk": child.pk}))
    assert response.context["ancestors"] == [category, parent]


@pytest.mark.django_db
def test_category_detail_shows_children_links(auth_client, category):
    child = Category.objects.create(name="Enfant", parent=category)
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    child_url = reverse("category-detail", kwargs={"pk": child.pk})
    assert f'href="{child_url}"' in response.content.decode()


@pytest.mark.django_db
def test_category_detail_shows_locked_child_without_link(auth_client, category, group):
    locked_child = Category.objects.create(name="Enfant restreint", parent=category)
    locked_child.groups.add(group)
    response = auth_client.get(reverse("category-detail", kwargs={"pk": category.pk}))
    content = response.content.decode()
    child_url = reverse("category-detail", kwargs={"pk": locked_child.pk})
    assert locked_child.name in content
    assert f'href="{child_url}"' not in content


@pytest.mark.django_db
def test_category_detail_locked_page_still_shows_hierarchy(auth_client, restricted_category):
    child = Category.objects.create(name="Enfant", parent=restricted_category)
    response = auth_client.get(reverse("category-detail", kwargs={"pk": restricted_category.pk}))
    assert response.context["children"].count() == 1
    assert child.name in response.content.decode()


# ---------------------------------------------------------------------------
# CategoryCreateView / CategoryUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_create_requires_staff(auth_client):
    response = auth_client.get(reverse("category-create"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_category_create_get_returns_200(staff_client):
    response = staff_client.get(reverse("category-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_category_create_get_loads_markdown_editor_widget(staff_client):
    response = staff_client.get(reverse("category-create"))
    content = response.content.decode()
    assert "js/markdown_editor.js" in content
    assert "markdown-editor-toolbar" in content


@pytest.mark.django_db
def test_category_create_post_creates_category(staff_client, db):
    response = staff_client.post(reverse("category-create"), {"name": "Nouvelle catégorie", "description": ""})
    assert response.status_code == 302
    assert Category.objects.filter(name="Nouvelle catégorie").exists()


@pytest.mark.django_db
def test_category_update_requires_staff(auth_client, category):
    response = auth_client.get(reverse("category-edit", kwargs={"pk": category.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_category_form_rejects_group_when_ancestor_restricted(staff_client, restricted_category, group):
    child = Category.objects.create(name="Enfant", parent=restricted_category)
    other_group = Group.objects.create(name="Autre")
    response = staff_client.post(
        reverse("category-edit", kwargs={"pk": child.pk}),
        {"name": "Enfant", "description": "", "parent": restricted_category.pk, "groups": [other_group.pk]},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_category_form_accepts_group_when_ancestry_public(staff_client, category, group):
    response = staff_client.post(
        reverse("category-edit", kwargs={"pk": category.pk}),
        {"name": category.name, "description": "", "groups": [group.pk]},
    )
    assert response.status_code == 302
    assert list(category.groups.all()) == [group]


@pytest.mark.django_db
def test_category_form_rejects_group_when_grandparent_restricted(staff_client, restricted_category, group):
    parent = Category.objects.create(name="Parent", parent=restricted_category)
    child = Category.objects.create(name="Enfant", parent=parent)
    other_group = Group.objects.create(name="Autre")
    response = staff_client.post(
        reverse("category-edit", kwargs={"pk": child.pk}),
        {"name": "Enfant", "description": "", "parent": parent.pk, "groups": [other_group.pk]},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_category_form_rejects_group_when_existing_category_has_restricted_descendant(staff_client, category, group):
    child = Category.objects.create(name="Enfant restreint", parent=category)
    child.groups.add(group)
    response = staff_client.post(
        reverse("category-edit", kwargs={"pk": category.pk}),
        {"name": category.name, "description": "", "groups": [group.pk]},
    )
    assert response.status_code == 200
    assert response.context["form"].errors


# ---------------------------------------------------------------------------
# CategoryDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_delete_requires_staff(auth_client, category):
    response = auth_client.get(reverse("category-delete", kwargs={"pk": category.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_category_delete_succeeds_when_empty(staff_client, category):
    response = staff_client.post(reverse("category-delete", kwargs={"pk": category.pk}))
    assert response.status_code == 302
    assert not Category.objects.filter(pk=category.pk).exists()


@pytest.mark.django_db
def test_category_delete_blocked_when_has_documents(staff_client, category, document):
    response = staff_client.post(reverse("category-delete", kwargs={"pk": category.pk}))
    assert response.status_code == 200
    assert Category.objects.filter(pk=category.pk).exists()


@pytest.mark.django_db
def test_category_delete_blocked_when_has_children(staff_client, category):
    Category.objects.create(name="Enfant", parent=category)
    response = staff_client.post(reverse("category-delete", kwargs={"pk": category.pk}))
    assert response.status_code == 200
    assert Category.objects.filter(pk=category.pk).exists()


@pytest.mark.django_db
def test_category_delete_get_shows_document_count(staff_client, category, document):
    response = staff_client.get(reverse("category-delete", kwargs={"pk": category.pk}))
    assert response.context["document_count"] == 1
