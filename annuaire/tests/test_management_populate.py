import pytest
from io import StringIO

from django.core.management import call_command

from annuaire.models import Account, Chalet, Person, PresencePSV, Relation
from publications.models import Attachment, BlogPost, Comment


# ------------------------------------------------------------------ helpers

@pytest.fixture(autouse=True)
def use_tmp_media(tmp_path, settings):
    """Redirect file uploads to a temp directory so tests don't pollute MEDIA_ROOT."""
    settings.MEDIA_ROOT = tmp_path


def run_populate(**kwargs):
    out = StringIO()
    call_command("populate_dev_data", stdout=out, **kwargs)
    return out.getvalue()


# ------------------------------------------------------------------ counts

@pytest.mark.django_db
class TestPopulateDevDataCounts:
    def test_model_counts(self):
        run_populate()
        # 20 regular persons + 1 staff person (admin has no Person)
        assert Person.objects.count() == 21
        # 20 regular accounts + admin + staff
        assert Account.objects.count() == 22
        assert Chalet.objects.count() == 5
        assert PresencePSV.objects.count() == 50
        # 30 directional relations created + 30 inverse relations via signal
        assert Relation.objects.count() == 60
        assert BlogPost.objects.count() == 30
        assert Attachment.objects.count() == 15
        assert Comment.objects.count() == 100

    def test_attachment_is_image_flags(self):
        run_populate()
        n_images = Attachment.objects.filter(is_image=True).count()
        n_files = Attachment.objects.filter(is_image=False).count()
        # Command creates (N_ATTACHMENTS * 2) // 3 images, rest non-image
        assert n_images == 10
        assert n_files == 5


# ------------------------------------------------------------------ account properties

@pytest.mark.django_db
class TestPopulateDevDataAccounts:
    def test_admin_is_superuser(self):
        run_populate()
        admin = Account.objects.get(email="admin@example.com")
        assert admin.is_superuser
        assert admin.is_staff
        assert not admin.must_change_password
        assert admin.check_password("admin")

    def test_staff_is_non_superuser_staff(self):
        run_populate()
        staff = Account.objects.get(email="staff@example.com")
        assert staff.is_staff
        assert not staff.is_superuser
        assert not staff.must_change_password
        assert staff.check_password("staff")

    def test_staff_has_linked_person_profile(self):
        run_populate()
        staff = Account.objects.get(email="staff@example.com")
        assert hasattr(staff, "profile")
        assert staff.profile.first_name == "Sandrine"

    def test_all_persons_linked_to_accounts(self):
        run_populate()
        assert Person.objects.filter(account__isnull=True).count() == 0

    def test_regular_accounts_use_dev_password(self):
        run_populate()
        regular = Account.objects.exclude(
            email__in=["admin@example.com", "staff@example.com"]
        ).first()
        assert regular.check_password("dev")
        assert not regular.must_change_password


# ------------------------------------------------------------------ flags

@pytest.mark.django_db
class TestPopulateDevDataFlags:
    def test_stdout_contains_test_credentials(self):
        output = run_populate()
        assert "admin@example.com" in output
        assert "staff@example.com" in output

    def test_second_default_run_clears_and_recreates(self):
        run_populate()
        run_populate()
        assert Person.objects.count() == 21
        assert Account.objects.count() == 22
        assert BlogPost.objects.count() == 30

    def test_no_clear_on_empty_db_behaves_like_normal_run(self):
        run_populate(no_clear=True)
        assert Person.objects.count() == 21
        assert Account.objects.count() == 22

    def test_no_clear_skips_existing_admin(self):
        # Pre-create admin so it exists before the command runs
        existing = Account.objects.create_superuser(
            email="admin@example.com", password="admin"
        )
        run_populate(no_clear=True)
        # Admin must not be duplicated
        assert Account.objects.filter(email="admin@example.com").count() == 1
        # The pre-existing admin object is still the same row
        assert Account.objects.get(email="admin@example.com").pk == existing.pk

    def test_no_clear_skips_existing_staff(self):
        existing = Account.objects.create_user(
            email="staff@example.com", password="staff", is_staff=True
        )
        run_populate(no_clear=True)
        assert Account.objects.filter(email="staff@example.com").count() == 1
        assert Account.objects.get(email="staff@example.com").pk == existing.pk

    def test_seed_reproducibility(self):
        run_populate(seed=99)
        names_first = sorted(
            Person.objects.values_list("first_name", "last_name")
        )
        run_populate(seed=99)  # clears and repopulates with same seed
        names_second = sorted(
            Person.objects.values_list("first_name", "last_name")
        )
        assert names_first == names_second

    def test_different_seeds_produce_different_data(self):
        run_populate(seed=1)
        names_seed1 = sorted(Person.objects.values_list("first_name", "last_name"))
        run_populate(seed=2)
        names_seed2 = sorted(Person.objects.values_list("first_name", "last_name"))
        assert names_seed1 != names_seed2
