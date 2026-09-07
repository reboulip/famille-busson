import pytest

from events.access import accessible_events, effective_groups, user_can_access_event


@pytest.mark.django_db
def test_effective_groups_empty_for_unrestricted_event(event):
    assert effective_groups(event) == []


@pytest.mark.django_db
def test_effective_groups_returns_event_groups(restricted_event, group):
    assert effective_groups(restricted_event) == [group]


@pytest.mark.django_db
def test_user_can_access_event_true_for_unrestricted(event, account):
    assert user_can_access_event(account, event) is True


@pytest.mark.django_db
def test_user_can_access_event_false_for_non_member(restricted_event, account):
    assert user_can_access_event(account, restricted_event) is False


@pytest.mark.django_db
def test_user_can_access_event_true_for_group_member(restricted_event, account, group):
    account.groups.add(group)
    assert user_can_access_event(account, restricted_event) is True


@pytest.mark.django_db
def test_user_can_access_event_true_for_staff(restricted_event, staff_account):
    assert user_can_access_event(staff_account, restricted_event) is True


@pytest.mark.django_db
def test_accessible_events_excludes_restricted_for_non_member(event, restricted_event, account):
    qs = accessible_events(account)
    assert event in qs
    assert restricted_event not in qs


@pytest.mark.django_db
def test_accessible_events_includes_restricted_for_group_member(restricted_event, account, group):
    account.groups.add(group)
    assert restricted_event in accessible_events(account)


@pytest.mark.django_db
def test_accessible_events_includes_everything_for_staff(event, restricted_event, staff_account):
    qs = accessible_events(staff_account)
    assert event in qs
    assert restricted_event in qs
