import pytest
from django.contrib.auth.models import Group

from documents.access import accessible_categories, accessible_documents, effective_groups, user_can_access_category
from documents.models import Category, Document


@pytest.mark.django_db
def test_user_can_access_public_category(account):
    category = Category.objects.create(name="Public")
    assert user_can_access_category(account, category) is True


@pytest.mark.django_db
def test_staff_bypasses_restriction(staff_account):
    category = Category.objects.create(name="Restreint")
    group = Group.objects.create(name="SCI")
    category.groups.add(group)
    assert user_can_access_category(staff_account, category) is True


@pytest.mark.django_db
def test_member_of_restricting_group_can_access(account):
    category = Category.objects.create(name="Restreint")
    group = Group.objects.create(name="SCI")
    category.groups.add(group)
    account.groups.add(group)
    assert user_can_access_category(account, category) is True


@pytest.mark.django_db
def test_non_member_cannot_access_restricted_category(account):
    category = Category.objects.create(name="Restreint")
    group = Group.objects.create(name="SCI")
    category.groups.add(group)
    assert user_can_access_category(account, category) is False


@pytest.mark.django_db
def test_effective_groups_inherits_from_restricted_ancestor():
    parent = Category.objects.create(name="Parent")
    group = Group.objects.create(name="SCI")
    parent.groups.add(group)
    child = Category.objects.create(name="Enfant", parent=parent)
    assert list(effective_groups(child)) == [group]


@pytest.mark.django_db
def test_effective_groups_empty_for_fully_public_chain():
    parent = Category.objects.create(name="Parent")
    child = Category.objects.create(name="Enfant", parent=parent)
    assert effective_groups(child) == []


@pytest.mark.django_db
def test_member_can_access_descendant_of_restricted_ancestor(account):
    parent = Category.objects.create(name="Parent")
    group = Group.objects.create(name="SCI")
    parent.groups.add(group)
    child = Category.objects.create(name="Enfant", parent=parent)
    account.groups.add(group)
    assert user_can_access_category(account, child) is True


@pytest.mark.django_db
def test_non_member_cannot_access_descendant_of_restricted_ancestor(account):
    parent = Category.objects.create(name="Parent")
    group = Group.objects.create(name="SCI")
    parent.groups.add(group)
    child = Category.objects.create(name="Enfant", parent=parent)
    assert user_can_access_category(account, child) is False


@pytest.mark.django_db
def test_accessible_categories_excludes_restricted_for_non_member(account):
    public = Category.objects.create(name="Public")
    restricted = Category.objects.create(name="Restreint")
    group = Group.objects.create(name="SCI")
    restricted.groups.add(group)
    result = accessible_categories(account)
    assert public in result
    assert restricted not in result


@pytest.mark.django_db
def test_accessible_categories_includes_all_for_staff(staff_account):
    public = Category.objects.create(name="Public")
    restricted = Category.objects.create(name="Restreint")
    group = Group.objects.create(name="SCI")
    restricted.groups.add(group)
    result = accessible_categories(staff_account)
    assert public in result
    assert restricted in result


@pytest.mark.django_db
def test_accessible_categories_excludes_descendant_of_restricted_ancestor(account):
    parent = Category.objects.create(name="Parent")
    group = Group.objects.create(name="SCI")
    parent.groups.add(group)
    child = Category.objects.create(name="Enfant", parent=parent)
    result = accessible_categories(account)
    assert parent not in result
    assert child not in result


@pytest.mark.django_db
def test_accessible_documents_excludes_documents_in_restricted_category(account):
    public = Category.objects.create(name="Public")
    restricted = Category.objects.create(name="Restreint")
    group = Group.objects.create(name="SCI")
    restricted.groups.add(group)
    doc_public = Document.objects.create(title="Doc public", category=public)
    doc_restricted = Document.objects.create(title="Doc restreint", category=restricted)
    result = accessible_documents(account)
    assert doc_public in result
    assert doc_restricted not in result
