"""Regression guard: per-file upload progress requires XMLHttpRequest --
fetch() cannot report xhr.upload.onprogress-style progress, so a future
"modernisation" swapping the transport would silently lose the progress bar.
No JS test runner in this project -- assert on the source text instead,
mirroring documents/tests/test_document_viewer_layout.py's approach."""

from pathlib import Path

PHOTO_UPLOAD_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "photo_upload.js"


def test_uses_xhr_with_upload_progress():
    content = PHOTO_UPLOAD_JS.read_text(encoding="utf-8")
    assert "new XMLHttpRequest()" in content
    assert "xhr.upload.addEventListener" in content


def test_does_not_use_fetch():
    content = PHOTO_UPLOAD_JS.read_text(encoding="utf-8")
    assert "fetch(" not in content
