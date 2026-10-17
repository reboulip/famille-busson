"""Regression guard for OSM tile usage policy compliance (#150). OSM's tile servers
started blocking this app's requests: Django's default Referrer-Policy is same-origin,
so a cross-origin tile <img> request carried no Referer at all, which OSM's policy
requires. Fix is a per-layer referrerPolicy override (not a site-wide settings change,
which would leak the site origin to every external link) plus the current
non-subdomain tile URL. No JS test runner in this project -- assert on map_init.js
source text, mirroring test_carte_marker_cluster.py's approach."""

from pathlib import Path

MAP_INIT_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "map_init.js"


def _content() -> str:
    return MAP_INIT_JS.read_text(encoding="utf-8")


def test_tile_url_uses_the_current_non_subdomain_endpoint():
    content = _content()
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in content
    assert "{s}.tile.openstreetmap.org" not in content


def test_tile_layer_sends_a_referrer():
    content = _content()
    assert "referrerPolicy: 'strict-origin-when-cross-origin'" in content


def test_attribution_and_max_zoom_unchanged():
    content = _content()
    assert "openstreetmap.org/copyright" in content
    assert "maxZoom: 19" in content


def test_no_retina_or_cache_busting_added():
    content = _content()
    assert "detectRetina" not in content
    assert "crossOrigin" not in content
