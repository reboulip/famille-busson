"""Regression guard for clustering co-located Carte markers: every co-located group
of CLUSTER_MIN_SIZE or more (persons and chalets alike) gets the composite "+N"
cluster pin, replacing the old spread-into-individual-markers behavior for small
groups (#114). No JS test runner in this project -- assert on map_init.js source
text, mirroring test_carte_dropdown_layering.py's approach. Supersedes
test_carte_marker_spread.py, which asserted the now-removed spread behavior."""

import re
from pathlib import Path

MAP_INIT_JS = Path(__file__).resolve().parent.parent / "static" / "js" / "map_init.js"


def _content() -> str:
    return MAP_INIT_JS.read_text(encoding="utf-8")


def test_spread_machinery_is_gone():
    content = _content()
    for removed in ("SPREAD_MAX", "SPREAD_RADIUS", "SPREAD_RING_STEP", "PER_RING", "calculateIconOffset"):
        assert removed not in content, f"{removed!r} should have been removed with the spread behavior"


def test_clusters_from_a_named_minimum_size():
    content = _content()
    match = re.search(r"const CLUSTER_MIN_SIZE\s*=\s*(\d+)", content)
    assert match
    assert int(match.group(1)) == 2
    assert "entries.length >= CLUSTER_MIN_SIZE" in content
    assert "buildClusterIcon" in content
    assert "map-marker-cluster-badge" in content


def test_markers_stay_at_the_group_s_true_coordinates():
    # The server contract (map_data.py) is untouched, and clustering must never
    # move a marker off its real point.
    content = _content()
    assert "L.marker([group.lat, group.lon]" in content


def test_person_and_cluster_icons_share_the_same_geometry_helper():
    # #114: with the spread offset gone, a solo icon and a cluster icon are
    # geometrically identical -- one shared factory, not two divergent ones.
    content = _content()
    assert "function buildMarkerIcon(" in content
    assert content.count("buildMarkerIcon(") >= 3  # definition + both call sites


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


def test_search_index_is_built_from_each_marker_s_entries():
    content = _content()
    assert "_entries" in content
    # Guards against reverting to the old per-group/per-entry-name index.
    assert "_entryName" not in content
    assert "_groupIdx" not in content


def test_both_persons_and_chalets_cluster_with_their_own_label():
    # #114 (user decision): chalets cluster too, not persons-only -- buildMarkers()
    # stays shared between both collections.
    content = _content()
    assert "buildMarkers(persons, 'membres')" in content
    assert "buildMarkers(chalets, 'chalets')" in content


def test_marker_avatar_carries_alt_text():
    content = _content()
    assert "img.alt = entryName || ''" in content


def test_search_result_bolds_the_matched_name_in_a_cluster_popup():
    content = _content()
    assert "map-marker-cluster-list li" in content
    assert "fw-bold" in content
