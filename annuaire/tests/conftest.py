import datetime

import pytest
from django.test import Client

from annuaire.models import Account, Chalet, Person, PresencePSV


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def account(db):
    return Account.objects.create_user(email="alice@example.com", password="testpass123!")


@pytest.fixture
def person(db, account):
    p = Person.objects.create(first_name="Alice", last_name="Busson", email="alice@example.com")
    p.account = account
    p.save()
    return p


@pytest.fixture
def other_account(db):
    return Account.objects.create_user(email="bob@example.com", password="testpass123!")


@pytest.fixture
def other_person(db, other_account):
    p = Person.objects.create(first_name="Bob", last_name="Busson", email="bob@example.com")
    p.account = other_account
    p.save()
    return p


@pytest.fixture
def auth_client(client, account, person):
    client.login(username="alice@example.com", password="testpass123!")
    return client


@pytest.fixture
def accountless_person(db):
    # Distinct/no email on purpose: link_account_to_person auto-links on Account
    # post_save by email match, which would silently make ownership tests vacuous
    # if this reused person/other_person's alice@/bob@example.com.
    return Person.objects.create(first_name="Charlie", last_name="Busson")


@pytest.fixture
def owned_person(accountless_person, person):
    accountless_person.owners.add(person)
    return accountless_person


@pytest.fixture
def staff_account(db):
    return Account.objects.create_user(email="staff@example.com", password="testpass123!", is_staff=True)


@pytest.fixture
def staff_client(client, staff_account):
    client.login(username="staff@example.com", password="testpass123!")
    return client


@pytest.fixture
def chalet(db):
    return Chalet.objects.create(name="Chalet des Alpes", address="Route des Alpes 1, Verbier")


@pytest.fixture
def presence(db, person, chalet):
    # Relative to today, not a hardcoded date -- a fixed future date eventually
    # becomes past and starts failing test_chalet_detail_context_has_future_presences.
    today = datetime.date.today()
    return PresencePSV.objects.create(
        person=person,
        chalet=chalet,
        start_date=today + datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=43),
    )
