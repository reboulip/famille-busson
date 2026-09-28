import io
import zipfile
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from annuaire.tests.conftest import (  # noqa: F401 — re-exported as fixtures
    account,
    auth_client,
    client,
    other_account,
    other_person,
    person,
    staff_account,
    staff_client,
)
from publications.models import Attachment, BlogPost, Comment, Tag

DEMO_BULLETIN_DIR = Path(settings.BASE_DIR) / "design" / "bulletins" / "prototype" / "fixtures" / "demo-001"


def _zip_demo_bulletin(**overrides) -> bytes:
    """Zips the synthetic demo-001 package (design/bulletins/prototype/fixtures/,
    never real family data -- see CLAUDE.md's source-text regression tests note).
    `overrides` replaces top-level keys of bulletin.json, for building invalid
    variants without hand-writing a whole package."""
    import json

    data = json.loads((DEMO_BULLETIN_DIR / "bulletin.json").read_text(encoding="utf-8"))
    data.update(overrides)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bulletin.json", json.dumps(data, ensure_ascii=False))
        for image_path in sorted((DEMO_BULLETIN_DIR / "images").iterdir()):
            zf.write(image_path, f"images/{image_path.name}")
    return buf.getvalue()


@pytest.fixture
def demo_bulletin_zip_bytes():
    return _zip_demo_bulletin()


@pytest.fixture
def demo_bulletin_zip(demo_bulletin_zip_bytes):
    return SimpleUploadedFile("demo-001.zip", demo_bulletin_zip_bytes, content_type="application/zip")


def add_bulletin_import_image(bulletin_import, image_id, filename="tiny.jpg"):
    """Stages one BulletinImportImage row -- shared by test_bulletin_models.py
    and test_views_bulletin.py, both of which need to make a BulletinImport
    publishable (apply_bulletin_import requires its declared images to exist)."""
    from publications.models import BulletinImportImage

    return BulletinImportImage.objects.create(
        bulletin_import=bulletin_import,
        image_id=image_id,
        file=SimpleUploadedFile(filename, b"\xff\xd8\xff\xdb fake jpeg bytes", content_type="image/jpeg"),
        kind="page",
        width=10,
        height=10,
        sha256="0" * 64,
    )


@pytest.fixture
def blog_post(db, person):
    post = BlogPost.objects.create(title="Première publication", body="Du contenu.")
    post.authors.add(person)
    return post


@pytest.fixture
def bc_post(db, person):
    tag, _created = Tag.objects.get_or_create(name="Busson connection", defaults={"accent": "gold"})
    post = BlogPost.objects.create(title="Annonce BC", body="Une annonce Busson connection.")
    post.authors.add(person)
    post.tags.add(tag)
    return post


@pytest.fixture
def other_blog_post(db, other_person):
    post = BlogPost.objects.create(title="Article de Bob", body="Le contenu de Bob.")
    post.authors.add(other_person)
    return post


@pytest.fixture
def comment(db, blog_post, person):
    return Comment.objects.create(post=blog_post, author=person, body="Bien dit.")


@pytest.fixture
def image_attachment(db, blog_post):
    uploaded = SimpleUploadedFile(
        name="photo.png",
        content=b"\x89PNG\r\n\x1a\nfake-png-bytes",
        content_type="image/png",
    )
    return Attachment.objects.create(post=blog_post, file=uploaded, caption="Une image")


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="Photos")


@pytest.fixture
def pdf_attachment(db, blog_post):
    uploaded = SimpleUploadedFile(
        name="doc.pdf",
        content=b"%PDF-fake",
        content_type="application/pdf",
    )
    return Attachment.objects.create(post=blog_post, file=uploaded, caption="Un PDF")
