import pytest
from django.core.management import call_command

from photos.models import Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_command_processes_pending_photos(album, capsys):
    Photo.objects.create(album=album, file=make_uploaded_image())
    call_command("generate_photo_derivatives")
    captured = capsys.readouterr()
    assert "1 photo(s) traitée(s)" in captured.out
    photo = Photo.objects.get()
    assert photo.derivative_status == "done"


@pytest.mark.django_db
def test_command_reports_nothing_to_process(capsys):
    call_command("generate_photo_derivatives")
    captured = capsys.readouterr()
    assert "Aucune photo à traiter." in captured.out
