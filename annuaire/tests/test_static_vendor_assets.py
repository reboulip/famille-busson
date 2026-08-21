"""Guard against the collectstatic-breaking bug class fixed in f9e9ee5: a vendored
CSS/JS file referencing a relative asset (image, font, sourcemap) that wasn't
actually committed. CompressedManifestStaticFilesStorage fails hard on this at
`collectstatic` time in production -- a step that never runs in CI -- so this test
is the only thing that would otherwise catch it before deploy."""

import re
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent / "static" / "vendor"

_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")#]+)\1\s*\)")
_SOURCEMAP_RE = re.compile(r"^//#\s*sourceMappingURL=(.+)$", re.MULTILINE)


def _is_external(reference: str) -> bool:
    return reference.startswith(("http://", "https://", "//", "data:"))


def test_vendored_css_url_references_exist():
    missing = []
    for css_file in VENDOR_DIR.rglob("*.css"):
        content = css_file.read_text(encoding="utf-8", errors="ignore")
        for match in _URL_RE.finditer(content):
            reference = match.group(2)
            if _is_external(reference):
                continue
            if not (css_file.parent / reference).resolve().exists():
                missing.append(f"{css_file.relative_to(VENDOR_DIR)}: url({reference})")
    assert not missing, f"Vendored CSS references missing assets: {missing}"


def test_vendored_js_sourcemaps_exist():
    missing = []
    for js_file in VENDOR_DIR.rglob("*.js"):
        content = js_file.read_text(encoding="utf-8", errors="ignore")
        match = _SOURCEMAP_RE.search(content)
        if match is None:
            continue
        reference = match.group(1).strip()
        if _is_external(reference):
            continue
        if not (js_file.parent / reference).resolve().exists():
            missing.append(f"{js_file.relative_to(VENDOR_DIR)}: sourceMappingURL={reference}")
    assert not missing, f"Vendored JS references missing sourcemaps: {missing}"
