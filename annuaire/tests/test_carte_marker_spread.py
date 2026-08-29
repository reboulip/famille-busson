"""Regression guard for spreading co-located Carte markers: groups of up to
SPREAD_MAX profiles at the same address get individual markers offset around
the shared point instead of one composite cluster pin, so overlapping avatars
stay visible. No JS test runner in this project -- assert on map_init.js
source text, mirroring test_carte_dropdown_layering.py's approach."""

import re
from pathlib import Path

MAP_INIT_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "map_init.js"


def _content() -> str:
    return MAP_INIT_JS.read_text(encoding="utf-8")


def test_defines_spread_constants():
    content = _content()
    for const in ("SPREAD_MAX", "SPREAD_RADIUS", "SPREAD_RING_STEP", "PER_RING"):
        assert re.search(rf"const {const}\s*=\s*\d+", content), f"Expected a {const} constant"


def test_spread_max_keeps_a_cluster_fallback_for_larger_groups():
    content = _content()
    match = re.search(r"const SPREAD_MAX\s*=\s*(\d+)", content)
    assert match
    assert int(match.group(1)) > 1
    # The composite "+N" cluster pin must still exist as the >SPREAD_MAX fallback.
    assert "buildClusterIcon" in content
    assert "map-marker-cluster-badge" in content


def test_offsets_icon_anchor_not_real_coordinates():
    content = _content()
    # The server contract (map_data.py) is untouched -- markers must stay at
    # the group's true lat/lon; only the icon/popup anchors move.
    assert "L.marker([group.lat, group.lon]" in content
    assert "iconAnchor: [half - dx, MARKER_SIZE - dy]" in content
    assert "popupAnchor: [dx, dy - MARKER_SIZE]" in content


def test_marker_size_is_a_single_constant_published_to_css():
    # Single source of truth (#85): JS and CSS must agree on marker size via
    # one shared custom property, not two independently-maintained numbers.
    content = _content()
    assert re.search(r"const MARKER_SIZE\s*=\s*\d+", content)
    assert "setProperty('--map-marker-size'" in content

    css_path = MAP_INIT_JS.resolve().parent.parent / "css" / "main.css"
    css_content = css_path.read_text(encoding="utf-8")
    assert "var(--map-marker-size" in css_content


def test_icon_sizes_derive_from_marker_size_not_hardcoded():
    content = _content()
    assert "iconSize: [MARKER_SIZE, MARKER_SIZE]" in content
    assert "iconSize: [40, 40]" not in content


def test_fit_bounds_counts_unique_group_points_not_flat_markers():
    content = _content()
    assert "uniquePointCount" in content
    assert "allMarkers.length === 1" not in content


def test_search_index_maps_each_entry_to_its_own_marker():
    content = _content()
    assert "_entryName" in content
    # Guards against reverting to the old per-group index (personMarkers[groupIdx]).
    assert "personMarkers[groupIdx]" not in content


def test_spread_marker_avatar_carries_alt_text():
    content = _content()
    assert "img.alt = entryName || ''" in content
