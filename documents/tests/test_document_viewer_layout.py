"""Regression guards for the document viewer overhaul (Phase 2, #98/#99/#100). These
properties can't be asserted through a rendered page (there's no JS test runner in
this project) -- assert on the source text of document_viewer.js/main.css instead,
mirroring test_genealogie_layout.py's approach."""

import re
from pathlib import Path

MAIN_CSS = Path(__file__).resolve().parent.parent.parent / "annuaire" / "static" / "css" / "main.css"
DOCUMENT_VIEWER_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "document_viewer.js"


def _strip_comments(css_text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)


def _rule_body(css_text: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css_text))
    assert match, f"No {selector!r} rule found in {MAIN_CSS}"
    return match.group(1)


def _declared_value(body: str, prop: str) -> str | None:
    match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else None


def test_document_viewer_stage_uses_the_shared_viewport_height_idiom():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer-stage")
    assert _declared_value(body, "height") == "70vh"
    assert _declared_value(body, "min-height") == "320px"


def test_document_viewer_fullscreen_is_a_fixed_overlay_above_offcanvas():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer--fullscreen")
    assert _declared_value(body, "position") == "fixed"
    z_index = _declared_value(body, "z-index")
    assert z_index is not None
    assert int(z_index) > 1045  # above the mobile offcanvas menu toggle


def test_document_viewer_js_toggles_fullscreen_class():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "document-viewer--fullscreen" in content


def test_document_viewer_js_exits_fullscreen_on_escape():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "'Escape'" in content or '"Escape"' in content


def test_document_viewer_js_never_references_field_file_url():
    # DocumentStorage.url() raises by design -- a viewer that builds URLs from
    # file.url instead of the document-file route would 500 the page.
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert ".file.url" not in content


def test_document_viewer_js_sets_pdfjs_worker_src_before_loading_document():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    worker_assignment = content.index("GlobalWorkerOptions.workerSrc")
    get_document_call = content.index("getDocument")
    assert worker_assignment < get_document_call
