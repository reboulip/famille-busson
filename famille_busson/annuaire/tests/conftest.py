import datetime
import pytest
from django.test import Client
from annuaire.models import Account, Person, Chalet, PresencePSV, Relation


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
def chalet(db):
    return Chalet.objects.create(name="Chalet des Alpes", address="Route des Alpes 1, Verbier")


@pytest.fixture
def presence(db, person, chalet):
    return PresencePSV.objects.create(
        person=person,
        chalet=chalet,
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 14),
    )
