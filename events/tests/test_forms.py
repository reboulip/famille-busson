import pytest

from events.forms import EventForm


@pytest.mark.django_db
def test_event_form_renders_hidden_coordinate_fields():
    form = EventForm()
    rendered = str(form)
    assert 'id="id_latitude"' in rendered
    assert 'id="id_longitude"' in rendered


@pytest.mark.django_db
def test_event_form_valid_with_minimal_data():
    form = EventForm(
        data={
            "title": "Pique-nique",
            "description": "",
            "start": "2026-07-14T12:00",
            "end": "2026-07-14T14:00",
            "location": "",
        }
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_event_form_pre_seeds_organisers_with_current_person(person):
    form = EventForm(current_person=person)
    assert form.fields["organisers"].initial == [person.pk]


@pytest.mark.django_db
def test_event_form_does_not_pre_seed_organisers_when_bound(person):
    form = EventForm(data={"title": "X", "start": "2026-07-14T12:00"}, current_person=person)
    assert form.fields["organisers"].initial is None
