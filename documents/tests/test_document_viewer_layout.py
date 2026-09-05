"""Regression guards for the document viewer overhaul (Phase 2, #98/#99/#100). These
properties can't be asserted through a rendered page (there's no JS test runner in
this project) -- assert on the source text of document_viewer.js/main.css instead,
mirroring test_genealogie_layout.py's approach."""

import re
from pathlib import Path

MAIN_CSS = Path(__file__).resolve().parent.parent.parent / "annuaire" / "static" / "css" / "main.css"
# The generic layout shell moved out of main.css into components.css with the
# Alpenglow design pass; main.css now holds only per-feature and vendor CSS.
COMPONENTS_CSS = Path(__file__).resolve().parent.parent.parent / "annuaire" / "static" / "css" / "components.css"
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


def test_document_viewer_js_calls_get_document_with_an_options_object():
    # Regression guard: pdf.js 6.x's getDocument(t = {}) reads t.url internally --
    # passing a bare URL string (rather than {url: ...}) is silently read as an empty
    # options object and fails at runtime with "expected either `data`, `range`, or
    # `url` parameter". No Python test can catch this (it's pure browser JS behavior);
    # caught only via live browser verification.
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "getDocument({ url: pdfUrl })" in content


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


def test_document_viewer_zoomed_image_rule_out_specifies_the_base_image_rule():
    # Regression guard for #111: a single-class ".document-viewer-zoomable--zoomed"
    # rule used to lose to the later, equally-specific ".document-file-preview-image"
    # rule -- the fix is a two-class selector combining both classes so it wins on
    # specificity regardless of source order.
    body = _rule_body(
        MAIN_CSS.read_text(encoding="utf-8"), ".document-file-preview-image.document-viewer-zoomable--zoomed"
    )
    assert _declared_value(body, "max-width") == "none"
    assert _declared_value(body, "max-height") == "none"
    assert _declared_value(body, "flex") == "none"


def test_document_viewer_fullscreen_carousel_shows_one_image_per_view():
    # Must be placed outside the @media (min-width: 992px) block, else the desktop
    # regression test above would read the wrong rule body (see that test's comment).
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer--fullscreen .document-viewer-strip-item")
    assert _declared_value(body, "flex") == "0 0 100%"


def test_document_viewer_fullscreen_carousel_snaps_to_exactly_one_image():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer--fullscreen .document-viewer-strip")
    assert _declared_value(body, "scroll-snap-type") == "x mandatory"


def test_document_viewer_js_defines_an_image_carousel():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "function initImageCarousel(" in content


def test_document_viewer_js_carousel_responds_to_arrow_keys_in_fullscreen():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "'ArrowLeft'" in content
    assert "'ArrowRight'" in content


def test_document_viewer_js_clicking_a_strip_image_enters_fullscreen_instead_of_zooming():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "isStripImage" in content
    assert "setFullscreen(true)" in content


# ---------------------------------------------------------------------------
# PDF rendering resolution, zoom and memory (#109)
# ---------------------------------------------------------------------------


def test_pdf_pages_render_at_the_device_pixel_ratio():
    """Rendering one canvas pixel per CSS pixel is what left scanned PDFs unreadable:
    a phone at devicePixelRatio 3 showed an A4 page through a 324-pixel-wide bitmap,
    and downloading the file was the only way to read it (#109)."""
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "window.devicePixelRatio" in content
    assert "cssScale * dpr" in content


def test_pdf_canvas_css_size_is_set_independently_of_its_backing_store():
    # The split is what lets the backing store carry dpr*zoom pixels, and lets a
    # released page keep its place in the scroll.
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "canvas.style.width" in content
    assert "canvas.style.height" in content


def test_pdf_page_css_rule_does_not_shrink_the_canvas_back_to_fit():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer-pdf-page")
    assert _declared_value(body, "max-width") == "none"


def test_pdf_viewer_offers_zoom_steps():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "PDF_ZOOM_STEPS" in content
    assert "document-viewer-zoom-in" in content
    assert "document-viewer-zoom-out" in content


def test_pdf_zoom_controls_are_rendered_in_the_pdf_toolbar():
    template = (Path(__file__).resolve().parent.parent / "templates" / "documents" / "document_detail.html").read_text(
        encoding="utf-8"
    )
    assert "document-viewer-zoom-in" in template
    assert "document-viewer-zoom-out" in template
    assert "document-viewer-zoom-level" in template


def test_pdf_pages_are_re_rendered_when_the_stage_changes_width():
    """Fullscreen used to show the same small page inside a bigger box: the canvases
    were sized once, at load, for the pre-fullscreen width (#109)."""
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "if (pdf) pdf.relayout();" in content
    assert "window.addEventListener('resize'" in content


def test_pdf_canvas_size_is_capped_per_page():
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "PDF_MAX_CANVAS_SIDE" in content
    assert "PDF_MAX_CANVAS_AREA" in content
    assert "function clampScale(" in content


def test_pdf_pages_release_their_pixels_once_far_off_screen():
    """Lazy *rendering* alone still accumulated every page ever shown -- 60 A4 pages at
    fit width is ~117M pixels of canvas that was never reclaimed (#109)."""
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "PDF_RETAIN_MARGIN" in content
    assert "function releasePage(" in content
    assert "entry.canvas.width = 1;" in content


def test_pdf_pages_start_with_a_collapsed_backing_store():
    # A not-yet-rendered canvas defaults to 300x150; 60 of them reserve ~11MB before a
    # single page is drawn.
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "canvas.width = 1;\n            canvas.height = 1;" in content


# ---------------------------------------------------------------------------
# Carousel / zoom layout (#111)
# ---------------------------------------------------------------------------


def test_carousel_counter_follows_a_manual_swipe():
    """The strip is a native scroll-snap container, so swiping (the primary mobile
    gesture) moves it without going through goTo(): the counter used to keep reading
    "1 / 4" after a swipe, and next/prev then stepped from the stale index (#111)."""
    content = DOCUMENT_VIEWER_JS.read_text(encoding="utf-8")
    assert "strip.addEventListener('scroll'" in content
    assert "currentIndex = closest;" in content


def test_content_column_can_shrink_below_its_content_width():
    """.fb-content is a flex item, and a flex item's default min-width: auto refuses to
    shrink below its content -- a zoomed image widened the whole page and made it
    scroll sideways, sidebar and all, instead of panning inside the viewer (#111).

    Was `.content` in main.css before the Alpenglow design pass renamed the shell
    and moved it to components.css; the guard is unchanged in substance."""
    body = _rule_body(COMPONENTS_CSS.read_text(encoding="utf-8"), ".fb-content")
    assert _declared_value(body, "min-width") == "0"


def test_document_viewer_stage_never_grows_past_its_column():
    body = _rule_body(MAIN_CSS.read_text(encoding="utf-8"), ".document-viewer-stage")
    assert _declared_value(body, "max-width") == "100%"
