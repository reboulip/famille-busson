import pytest

from photos.access import accessible_albums, accessible_photos, effective_groups, user_can_access_album
from photos.models import Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_user_can_access_public_album(account, album):
    assert user_can_access_album(account, album) is True


@pytest.mark.django_db
def test_staff_bypasses_restriction(staff_account, restricted_album):
    assert user_can_access_album(staff_account, restricted_album) is True


@pytest.mark.django_db
def test_member_of_restricting_group_can_access(account, restricted_album, group):
    account.groups.add(group)
    assert user_can_access_album(account, restricted_album) is True


@pytest.mark.django_db
def test_non_member_cannot_access_restricted_album(account, restricted_album):
    assert user_can_access_album(account, restricted_album) is False


@pytest.mark.django_db
def test_effective_groups_empty_for_public_album(album):
    assert effective_groups(album) == []


@pytest.mark.django_db
def test_effective_groups_returns_restricting_groups(restricted_album, group):
    assert list(effective_groups(restricted_album)) == [group]


@pytest.mark.django_db
def test_accessible_albums_excludes_restricted_for_non_member(account, album, restricted_album):
    result = accessible_albums(account)
    assert album in result
    assert restricted_album not in result


@pytest.mark.django_db
def test_accessible_albums_includes_restricted_for_member(account, restricted_album, group):
    account.groups.add(group)
    assert restricted_album in accessible_albums(account)


@pytest.mark.django_db
def test_accessible_albums_is_everything_for_staff(staff_account, album, restricted_album):
    result = accessible_albums(staff_account)
    assert album in result
    assert restricted_album in result


@pytest.mark.django_db
def test_accessible_photos_excludes_restricted_album_photos(account, album, restricted_album):
    visible = Photo.objects.create(album=album, file=make_uploaded_image())
    hidden = Photo.objects.create(album=restricted_album, file=make_uploaded_image())
    result = accessible_photos(account)
    assert visible in result
    assert hidden not in result
