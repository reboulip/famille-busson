import json
from decimal import Decimal

import pytest
from django.urls import reverse

from annuaire.models import Person, Relation, Settings

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# my_profile
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_my_profile_requires_login(client):
    response = client.get(reverse("my-profile"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_my_profile_redirects_to_person_detail(auth_client, person):
    response = auth_client.get(reverse("my-profile"))
    assert response.status_code == 302
    assert reverse("personne-detail", kwargs={"pk": person.pk}) in response["Location"]


@pytest.mark.django_db
def test_my_profile_no_profile_redirects_to_create(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("my-profile"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


# ---------------------------------------------------------------------------
# edit_my_profile
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_edit_my_profile_requires_login(client):
    response = client.get(reverse("edit-my-profile"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_edit_my_profile_redirects_to_person_edit(auth_client, person):
    response = auth_client.get(reverse("edit-my-profile"))
    assert response.status_code == 302
    assert reverse("person-edit", kwargs={"pk": person.pk}) in response["Location"]


@pytest.mark.django_db
def test_edit_my_profile_no_profile_redirects_to_create(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("edit-my-profile"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


# ---------------------------------------------------------------------------
# DirectoryListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_directory_requires_login(client):
    response = client.get(reverse("directory"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_directory_returns_200(auth_client):
    response = auth_client.get(reverse("directory"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_directory_lists_all_persons(auth_client, person, other_person):
    response = auth_client.get(reverse("directory"))
    assert person in response.context["persons"]
    assert other_person in response.context["persons"]


@pytest.mark.django_db
def test_directory_search_filters_by_name(auth_client, person, other_person):
    response = auth_client.get(reverse("directory") + "?q=Alice")
    assert person in response.context["persons"]
    assert other_person not in response.context["persons"]


@pytest.mark.django_db
def test_directory_search_no_results(auth_client, person):
    response = auth_client.get(reverse("directory") + "?q=zzznomatch")
    assert list(response.context["persons"]) == []


@pytest.mark.django_db
def test_directory_does_not_show_postal_address(auth_client, person):
    person.postal_address = "8 Boulevard du Port, 80000 Amiens"
    person.save()
    response = auth_client.get(reverse("directory"))
    assert person.first_name.encode() in response.content
    assert b"Boulevard du Port" not in response.content


# ---------------------------------------------------------------------------
# ProfileDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_detail_requires_login(client, person):
    response = client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_detail_returns_200(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_profile_detail_contact_info_each_on_its_own_line(auth_client, person):
    person.phone_number = "+33 6 12 34 56 78"
    person.postal_address = "1 rue de la République, Lyon"
    person.birth_date = "1990-01-01"
    person.save()
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert content.count('class="contact-line') == 4
    assert " - ☎️" not in content


@pytest.mark.django_db
def test_profile_detail_phone_link_uses_tel_scheme(auth_client, person):
    person.phone_number = "+33 6 12 34 56 78"
    person.save()
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert 'href="tel:+33 6 12 34 56 78"' in content
    assert "sip:" not in content


@pytest.mark.django_db
def test_profile_detail_context_has_person(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context["person"] == person


@pytest.mark.django_db
def test_profile_detail_shows_partner(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context.get("partner") == other_person


@pytest.mark.django_db
def test_profile_detail_shows_parents(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert other_person in response.context["parents"]


@pytest.mark.django_db
def test_profile_detail_shows_children(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=3)
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert other_person in response.context["children"]


@pytest.mark.django_db
def test_profile_detail_can_edit_true_for_own_profile(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_profile_detail_can_edit_false_for_other_profile(auth_client, other_person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": other_person.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_profile_detail_can_edit_true_for_staff(staff_client, other_person):
    response = staff_client.get(reverse("personne-detail", kwargs={"pk": other_person.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_profile_detail_shows_family_tree_link_for_own_profile(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert reverse("genealogie-person", kwargs={"pk": person.pk}) in response.content.decode()


@pytest.mark.django_db
def test_profile_detail_shows_family_tree_link_for_other_profile(auth_client, other_person):
    # Viewing the tree is a read action, unlike "Modifier le profil" -- available
    # regardless of can_edit.
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": other_person.pk}))
    assert reverse("genealogie-person", kwargs={"pk": other_person.pk}) in response.content.decode()


@pytest.mark.django_db
def test_profile_detail_does_not_display_gender(auth_client, person):
    # Person.gender was dropped entirely (#59) -- this guard stays as a regression
    # check that no such field ever resurfaces on the profile display page.
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert "Homme" not in content
    assert "Genre" not in content


# ---------------------------------------------------------------------------
# ProfileUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_update_requires_login(client, person):
    response = client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_update_own_profile_get_200(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_update_other_profile_returns_403(auth_client, other_person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": other_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_update_other_profile_post_returns_403(auth_client, other_person):
    data = {"first_name": other_person.first_name, "last_name": other_person.last_name}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": other_person.pk}), data)
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_update_staff_can_edit_any_profile(staff_client, other_person):
    response = staff_client.get(reverse("person-edit", kwargs={"pk": other_person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_update_staff_redirects_to_person_detail_after_save(staff_client, other_person):
    data = {"first_name": other_person.first_name, "last_name": other_person.last_name}
    data.update(_empty_formset_data())
    response = staff_client.post(reverse("person-edit", kwargs={"pk": other_person.pk}), data)
    assert response.status_code == 302
    assert reverse("personne-detail", kwargs={"pk": other_person.pk}) in response["Location"]


@pytest.mark.django_db
def test_profile_update_invalid_pk_returns_404(auth_client):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": 99999}))
    assert response.status_code == 404


def _empty_formset_data(prefix="ascending_relations"):
    """Return management form data for the RelationEditFormSet (prefix = related_name on person1 FK)."""
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.mark.django_db
def test_profile_update_post_valid_updates_person(auth_client, person):
    data = {"first_name": "Alicia", "last_name": "Busson"}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.refresh_from_db()
    assert person.first_name == "Alicia"


@pytest.mark.django_db
def test_profile_update_post_invalid_returns_200_with_errors(auth_client, person):
    data = {"first_name": "", "last_name": ""}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_update_form_has_multipart_enctype(auth_client, person):
    # Without this, browsers silently drop file input content on submit -- the
    # Django test client isn't affected (it always encodes files correctly
    # regardless of the template), so only an HTML assertion catches this.
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert 'enctype="multipart/form-data"' in response.content.decode()


# ---------------------------------------------------------------------------
# Notification preferences (3.5)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_update_renders_notification_checkboxes(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert "notify_on_birthday" in content
    assert "notify_on_new_blog_post" in content


@pytest.mark.django_db
def test_profile_update_prechecks_current_notification_prefs(auth_client, person):
    person.settings.notify_on_birthday = True
    person.settings.save()
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert response.context["settings_form"].initial["notify_on_birthday"] is True


@pytest.mark.django_db
def test_profile_update_post_saves_notification_prefs(auth_client, person):
    data = {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "notify_on_birthday": "on",
        "notify_on_new_blog_post": "on",
    }
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.settings.refresh_from_db()
    assert person.settings.notify_on_birthday is True
    assert person.settings.notify_on_new_blog_post is True


@pytest.mark.django_db
def test_profile_update_post_unchecked_boxes_unsubscribe(auth_client, person):
    person.settings.notify_on_birthday = True
    person.settings.notify_on_new_blog_post = True
    person.settings.save()
    data = {"first_name": person.first_name, "last_name": person.last_name}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.settings.refresh_from_db()
    assert person.settings.notify_on_birthday is False
    assert person.settings.notify_on_new_blog_post is False


@pytest.mark.django_db
def test_profile_update_post_invalid_leaves_notification_prefs_unchanged(auth_client, person):
    person.settings.notify_on_birthday = True
    person.settings.save()
    data = {"first_name": "", "last_name": "", "notify_on_birthday": "on"}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 200
    person.settings.refresh_from_db()
    assert person.settings.notify_on_birthday is True


@pytest.mark.django_db
def test_profile_update_heals_missing_settings_row(auth_client, person):
    Settings.objects.filter(person=person).delete()
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200
    assert Settings.objects.filter(person=person).exists()

    data = {"first_name": person.first_name, "last_name": person.last_name, "notify_on_birthday": "on"}
    data.update(_empty_formset_data())
    Settings.objects.filter(person=person).delete()
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    assert Settings.objects.get(person=person).notify_on_birthday is True


# ---------------------------------------------------------------------------
# Address autocomplete (ANN-A)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_update_renders_address_picker(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert "js/address_picker.js" in content
    assert "address-picker-input" in content


@pytest.mark.django_db
def test_profile_create_renders_address_picker(client, account):
    client.login(username=account.email, password="testpass123!")
    response = client.get(reverse("profile-create"))
    content = response.content.decode()
    assert "js/address_picker.js" in content
    assert "address-picker-input" in content


def test_profile_edit_form_address_widget_attrs():
    from annuaire.forms import ProfileEditForm

    widget = ProfileEditForm().fields["postal_address"].widget
    assert widget.attrs["autocomplete"] == "off"
    assert "address-picker-input" in widget.attrs["class"]
    assert str(widget.attrs["data-search-url"]) == reverse("address-search-ajax")


@pytest.mark.django_db
def test_profile_update_saves_ban_formatted_address(auth_client, person):
    data = {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "postal_address": "8 Boulevard du Port, 80000 Amiens",
    }
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.refresh_from_db()
    assert person.postal_address == "8 Boulevard du Port, 80000 Amiens"


@pytest.mark.django_db
def test_profile_update_saves_free_text_foreign_address(auth_client, person):
    data = {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "postal_address": "10 Downing Street, London SW1A 2AA, UK",
    }
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.refresh_from_db()
    assert person.postal_address == "10 Downing Street, London SW1A 2AA, UK"


@pytest.mark.django_db
def test_profile_update_photo_too_large_returns_form_error(auth_client, person, monkeypatch):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    import annuaire.forms as annuaire_forms

    monkeypatch.setattr(annuaire_forms, "PROFILE_PHOTO_MAX_SIZE_MB", 0)
    # Must be a genuinely valid image -- ImageField's Pillow validation runs before
    # the custom size check and rejects hand-crafted/corrupt bytes first.
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    tiny_png = SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")

    data = {"first_name": person.first_name, "last_name": person.last_name, "profile_photo": tiny_png}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 200
    assert "trop volumineuse" in response.content.decode()


# ---------------------------------------------------------------------------
# ProfileCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_create_requires_login(client):
    response = client.get(reverse("profile-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_create_get_returns_200(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("profile-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_create_redirects_if_profile_exists(auth_client, person):
    response = auth_client.get(reverse("profile-create"))
    assert response.status_code == 302
    assert reverse("my-profile") in response["Location"]


@pytest.mark.django_db
def test_profile_create_post_creates_person_and_links_account(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(
        reverse("profile-create"),
        {"first_name": "Alice", "last_name": "Busson"},
    )
    assert response.status_code == 302
    from annuaire.models import Person

    person = Person.objects.get(account=account)
    assert person.first_name == "Alice"
    assert reverse("personne-detail", kwargs={"pk": person.pk}) in response["Location"]


@pytest.mark.django_db
def test_profile_create_post_invalid_returns_200_with_errors(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(reverse("profile-create"), {"first_name": "", "last_name": ""})
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_profile_create_saves_notification_opt_ins(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(
        reverse("profile-create"),
        {
            "first_name": "Alice",
            "last_name": "Busson",
            "notify_on_birthday": "on",
            "notify_on_new_blog_post": "on",
        },
    )
    assert response.status_code == 302
    from annuaire.models import Person

    person = Person.objects.get(account=account)
    assert person.settings.notify_on_birthday is True
    assert person.settings.notify_on_new_blog_post is True


@pytest.mark.django_db
def test_profile_create_address_widget_has_coordinate_targets(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("profile-create"))
    content = response.content.decode()
    assert 'data-lat-target="id_latitude"' in content
    assert 'data-lon-target="id_longitude"' in content


@pytest.mark.django_db
def test_profile_create_saves_coordinates_from_hidden_fields(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(
        reverse("profile-create"),
        {
            "first_name": "Alice",
            "last_name": "Busson",
            "postal_address": "8 Boulevard du Port, 80000 Amiens",
            "latitude": "49.031624",
            "longitude": "2.062821",
        },
    )
    assert response.status_code == 302
    person = Person.objects.get(account=account)
    assert person.latitude == Decimal("49.031624")
    assert person.longitude == Decimal("2.062821")


@pytest.mark.django_db
def test_profile_create_without_opt_ins_defaults_to_false(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(reverse("profile-create"), {"first_name": "Alice", "last_name": "Busson"})
    assert response.status_code == 302
    from annuaire.models import Person

    person = Person.objects.get(account=account)
    assert person.settings.notify_on_birthday is False
    assert person.settings.notify_on_new_blog_post is False


# ---------------------------------------------------------------------------
# PersonRelationsView (GET)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_person_relations_requires_login(client, person):
    response = client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_person_relations_forbidden_for_other_user(auth_client, other_person):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": other_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_person_relations_allowed_for_owner(auth_client, person):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_relations_allowed_for_staff(staff_client, person):
    response = staff_client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_relations_404_for_invalid_pk(auth_client):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_person_relations_lists_existing(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    row_forms = response.context["row_forms"]
    assert len(row_forms) == 1
    relation, _form = row_forms[0]
    assert relation.person2 == other_person


# ---------------------------------------------------------------------------
# AddRelationView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_relation_creates_relation_and_inverse(auth_client, person, other_person):
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": person.pk}),
        {"person2": other_person.pk, "relationship_type": 2},
    )
    assert response.status_code == 302
    assert Relation.objects.filter(person1=person, person2=other_person, relationship_type=2).exists()
    # inverse: parent -> enfant
    assert Relation.objects.filter(person1=other_person, person2=person, relationship_type=3).exists()


@pytest.mark.django_db
def test_add_relation_rejects_self(auth_client, person):
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": person.pk}),
        {"person2": person.pk, "relationship_type": 2},
    )
    assert response.status_code == 302
    assert not Relation.objects.filter(person1=person).exists()


@pytest.mark.django_db
def test_add_relation_rejects_duplicate(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": person.pk}),
        {"person2": other_person.pk, "relationship_type": 1},
    )
    assert response.status_code == 302
    assert Relation.objects.filter(person1=person, person2=other_person).count() == 1


@pytest.mark.django_db
def test_add_relation_forbidden_for_other_user(auth_client, other_person, person):
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": other_person.pk}),
        {"person2": person.pk, "relationship_type": 2},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# UpdateRelationView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_update_relation_changes_type(auth_client, person, other_person):
    relation = Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-update", kwargs={"pk": person.pk, "rid": relation.pk}),
        {f"rel-{relation.pk}-relationship_type": "3", f"rel-{relation.pk}-start_date": ""},
    )
    assert response.status_code == 302
    relation.refresh_from_db()
    assert relation.relationship_type == 3


@pytest.mark.django_db
def test_update_relation_404_for_other_person_relation(auth_client, person, other_person):
    foreign = Person.objects.create(first_name="Foreign", last_name="Person")
    relation = Relation.objects.create(person1=other_person, person2=foreign, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-update", kwargs={"pk": person.pk, "rid": relation.pk}),
        {f"rel-{relation.pk}-relationship_type": "3"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DeleteRelationView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_relation_removes_both_sides(auth_client, person, other_person):
    relation = Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    inverse = Relation.objects.get(person1=other_person, person2=person)
    response = auth_client.post(
        reverse("person-relation-delete", kwargs={"pk": person.pk, "rid": relation.pk}),
    )
    assert response.status_code == 302
    assert not Relation.objects.filter(pk=relation.pk).exists()
    assert not Relation.objects.filter(pk=inverse.pk).exists()


@pytest.mark.django_db
def test_delete_relation_forbidden_for_other_user(auth_client, other_person, person):
    relation = Relation.objects.create(person1=other_person, person2=person, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-delete", kwargs={"pk": other_person.pk, "rid": relation.pk}),
    )
    assert response.status_code == 403
    assert Relation.objects.filter(pk=relation.pk).exists()


@pytest.mark.django_db
def test_delete_relation_404_for_other_person_relation(auth_client, person, other_person):
    foreign = Person.objects.create(first_name="Foreign", last_name="Person")
    relation = Relation.objects.create(person1=other_person, person2=foreign, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-delete", kwargs={"pk": person.pk, "rid": relation.pk}),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# MapListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_carte_requires_login(client):
    response = client.get(reverse("carte"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_carte_returns_200(auth_client):
    response = auth_client.get(reverse("carte"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_carte_includes_persons_with_coordinates(auth_client, person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    response = auth_client.get(reverse("carte"))
    assert person in response.context["persons"]


@pytest.mark.django_db
def test_carte_excludes_persons_without_coordinates(auth_client, person):
    response = auth_client.get(reverse("carte"))
    assert person not in response.context["persons"]


@pytest.mark.django_db
def test_carte_unresolved_count(auth_client, person, other_person):
    other_person.latitude = Decimal("49.0")
    other_person.longitude = Decimal("2.0")
    other_person.save()
    response = auth_client.get(reverse("carte"))
    assert response.context["unresolved_count"] == 1


@pytest.mark.django_db
def test_carte_persons_json_includes_name_and_profile_link(auth_client, person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    response = auth_client.get(reverse("carte"))
    content = response.content.decode()
    assert person.first_name in content
    assert reverse("personne-detail", kwargs={"pk": person.pk}) in content


@pytest.mark.django_db
def test_carte_persons_json_includes_avatar(auth_client, person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    response = auth_client.get(reverse("carte"))
    persons = json.loads(response.context["persons_json"])
    assert persons[0]["entries"][0]["avatar"]


@pytest.mark.django_db
def test_carte_includes_chalets_with_coordinates(auth_client, chalet):
    chalet.latitude = Decimal("46.096")
    chalet.longitude = Decimal("7.228")
    chalet.save()
    response = auth_client.get(reverse("carte"))
    chalets = json.loads(response.context["chalets_json"])
    assert chalets[0]["entries"][0]["name"] == chalet.name
    assert chalets[0]["entries"][0]["url"] == reverse("chalet-detail", kwargs={"pk": chalet.pk})


@pytest.mark.django_db
def test_carte_excludes_chalets_without_coordinates(auth_client, chalet):
    response = auth_client.get(reverse("carte"))
    chalets = json.loads(response.context["chalets_json"])
    assert chalets == []


@pytest.mark.django_db
def test_carte_unresolved_chalet_count(auth_client, chalet):
    response = auth_client.get(reverse("carte"))
    assert response.context["unresolved_chalet_count"] == 1


@pytest.mark.django_db
def test_carte_chalet_without_photo_uses_emoji_sentinel(auth_client, chalet):
    chalet.latitude = Decimal("46.096")
    chalet.longitude = Decimal("7.228")
    chalet.save()
    response = auth_client.get(reverse("carte"))
    chalets = json.loads(response.context["chalets_json"])
    assert chalets[0]["entries"][0]["avatar"] == "emoji::🏔️"


@pytest.mark.django_db
def test_carte_groups_persons_at_same_address(auth_client, person, other_person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    other_person.latitude = Decimal("49.031624")
    other_person.longitude = Decimal("2.062821")
    other_person.save()
    response = auth_client.get(reverse("carte"))
    persons = json.loads(response.context["persons_json"])
    assert len(persons) == 1
    assert len(persons[0]["entries"]) == 2


@pytest.mark.django_db
def test_carte_does_not_group_persons_at_different_addresses(auth_client, person, other_person):
    person.latitude = Decimal("49.031624")
    person.longitude = Decimal("2.062821")
    person.save()
    other_person.latitude = Decimal("46.096")
    other_person.longitude = Decimal("7.228")
    other_person.save()
    response = auth_client.get(reverse("carte"))
    persons = json.loads(response.context["persons_json"])
    assert len(persons) == 2
    assert all(len(group["entries"]) == 1 for group in persons)


@pytest.mark.django_db
def test_carte_renders_person_search_box(auth_client):
    response = auth_client.get(reverse("carte"))
    content = response.content.decode()
    assert 'id="carte-person-search"' in content
    assert "Rechercher un membre" in content
