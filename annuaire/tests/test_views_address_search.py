import pytest
from django.urls import reverse

LOGIN_URL = "/annuaire/login/"


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.mark.django_db
def test_address_search_requires_login(client):
    response = client.get(reverse("address-search-ajax"), {"q": "8 rue de la Paix"})
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_address_search_short_query_returns_empty(auth_client):
    response = auth_client.get(reverse("address-search-ajax"), {"q": "ab"})
    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_address_search_returns_normalized_results(auth_client, monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(
            {
                "features": [
                    {
                        "geometry": {"coordinates": [2.062821, 49.031624]},
                        "properties": {
                            "label": "8 Boulevard du Port 80000 Amiens",
                            "context": "Somme, Hauts-de-France",
                            "score": 0.9,
                            "name": "8 Boulevard du Port",
                            "postcode": "80000",
                            "city": "Amiens",
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    response = auth_client.get(reverse("address-search-ajax"), {"q": "8 Boulevard du Port"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["source"] == "ban"
    assert result["lat"] == "49.031624"
    assert result["lon"] == "2.062821"
    assert result["label"]
    assert result["address"]


@pytest.mark.django_db
def test_address_search_provider_failure_returns_empty_results(auth_client, monkeypatch):
    import requests

    def fake_get(url, params=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr("annuaire.geocoding.requests.get", fake_get)
    response = auth_client.get(reverse("address-search-ajax"), {"q": "adresse quelconque"})
    assert response.status_code == 200
    assert response.json() == {"results": []}
