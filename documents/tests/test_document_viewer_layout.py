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


def test_document_viewer_carousel_strip_is_one_item_per_row_by_default():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer-strip-item")
    assert _declared_value(body, "flex") == "0 0 100%"


def test_document_viewer_carousel_strip_shows_several_per_row_on_desktop():
    # This file has multiple `.document-viewer-strip-item` rules (mobile default +
    # desktop override) and multiple unrelated `@media (min-width: 992px)` blocks
    # elsewhere -- find the specific media block that contains this selector.
    css_text = _strip_comments(MAIN_CSS.read_text(encoding="utf-8"))
    for match in re.finditer(r"@media \(min-width: 992px\)\s*\{(.*?)\n\}", css_text, re.DOTALL):
        block = match.group(1)
        if ".document-viewer-strip-item" not in block:
            continue
        body = _rule_body(block, ".document-viewer-strip-item")
        flex_value = _declared_value(body, "flex")
        assert flex_value is not None
        assert "100%" not in flex_value  # must differ from the mobile one-per-row value
        return
    raise AssertionError("No @media (min-width: 992px) block containing .document-viewer-strip-item found")


def test_document_viewer_strip_scrolls_horizontally_with_native_touch_swipe():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer-stage.document-viewer-strip")
    assert _declared_value(body, "overflow-x") == "auto"


def test_document_viewer_js_toggles_zoom_class():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "document-viewer-zoomable--zoomed" in content


def test_document_viewer_zoom_uses_pinch_zoom_touch_action_not_a_custom_gesture_handler():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer-zoomable")
    assert _declared_value(body, "touch-action") == "pinch-zoom"
