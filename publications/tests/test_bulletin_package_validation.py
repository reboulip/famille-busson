import io
import json
import zipfile

import pytest

from publications.bulletin_package import PackageValidationError, flatten_bulletin_text, validate_package
from publications.tests.conftest import DEMO_BULLETIN_DIR


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, payload in entries.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def test_valid_package_has_no_errors(demo_bulletin_zip_bytes):
    result = validate_package(io.BytesIO(demo_bulletin_zip_bytes))
    assert result.errors == []
    assert result.data["id"] == "demo-001"
    assert set(result.images) == {img["id"] for img in result.data["images"]}


def test_valid_package_reports_stats(demo_bulletin_zip_bytes):
    result = validate_package(io.BytesIO(demo_bulletin_zip_bytes))
    assert result.stats["pictures"] > 0


def test_bad_zip_is_rejected():
    with pytest.raises(PackageValidationError):
        validate_package(io.BytesIO(b"not a zip file"))


def test_missing_bulletin_json_is_rejected():
    payload = _zip_bytes({"images/foo.jpg": b"whatever"})
    with pytest.raises(PackageValidationError):
        validate_package(io.BytesIO(payload))


def test_path_traversal_is_rejected():
    payload = _zip_bytes({"bulletin.json": b"{}", "images/../../etc/passwd": b"x"})
    with pytest.raises(PackageValidationError):
        validate_package(io.BytesIO(payload))


def test_unexpected_file_is_rejected():
    payload = _zip_bytes({"bulletin.json": b"{}", "not_allowed.txt": b"x"})
    with pytest.raises(PackageValidationError):
        validate_package(io.BytesIO(payload))


def test_schema_violation_is_rejected():
    # Missing every required top-level key.
    payload = _zip_bytes({"bulletin.json": json.dumps({}).encode()})
    with pytest.raises(PackageValidationError):
        validate_package(io.BytesIO(payload))


def test_sha256_mismatch_is_a_semantic_error(demo_bulletin_zip_bytes):
    with zipfile.ZipFile(io.BytesIO(demo_bulletin_zip_bytes)) as zf:
        names = zf.namelist()
        image_name = next(n for n in names if n.startswith("images/"))
        entries = {n: zf.read(n) for n in names}
    entries[image_name] = b"\x00" * len(entries[image_name])  # corrupt the bytes, same size
    payload = _zip_bytes(entries)

    result = validate_package(io.BytesIO(payload))
    assert any("sha256 mismatch" in error for error in result.errors)


def test_unreferenced_image_is_a_warning():
    data = json.loads((DEMO_BULLETIN_DIR / "bulletin.json").read_text(encoding="utf-8"))
    extra_id = f"{data['id']}-unused"
    data["images"].append(
        {
            "id": extra_id,
            "file": f"images/{extra_id}.jpg",
            "kind": "page",
            "media_type": "image/jpeg",
            "width": 10,
            "height": 10,
            "sha256": "0" * 64,
            "source": {"page": 1},
            "alt": "inutilisée",
        }
    )
    payload = _zip_bytes(
        {
            "bulletin.json": json.dumps(data).encode(),
            f"images/{extra_id}.jpg": b"not a real image",
        }
    )
    result = validate_package(io.BytesIO(payload))
    # The corrupt/unreadable extra image is its own semantic error, and since it's
    # never referenced from an article it also produces a warning -- both checks fire.
    assert any(extra_id in warning for warning in result.warnings)


def test_flatten_bulletin_text_includes_summary_and_article_text():
    data = json.loads((DEMO_BULLETIN_DIR / "bulletin.json").read_text(encoding="utf-8"))
    text = flatten_bulletin_text(data)
    assert data["summary"] in text
