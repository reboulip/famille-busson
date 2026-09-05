"""Regression guards for Carte marker clustering (#114). The Carte now uses
Leaflet.markercluster, so clusters merge and split with the zoom level instead of being
computed once at load: zoom out and co-located people collapse into one counted pin,
zoom in and they separate. Because everyone at one address shares identical
coordinates -- which no amount of zooming can pull apart -- map_init.js first spreads
each co-located group onto a small ring around its true point.

No JS test runner in this project -- assert on map_init.js source text, mirroring
test_carte_dropdown_layering.py's approach. Supersedes the previous fixed
"+N cluster pin for every group of 2+" guards, which asserted a behavior that
markercluster now supplies dynamically."""

import re
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MAP_INIT_JS = STATIC_DIR / "js" / "map_init.js"
CARTE_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "annuaire" / "carte.html"
MARKERCLUSTER_DIR = STATIC_DIR / "vendor" / "leaflet.markercluster"


def _content() -> str:
    return MAP_INIT_JS.read_text(encoding="utf-8")


def test_spread_machinery_is_gone():
    content = _content()
    for removed in ("SPREAD_MAX", "SPREAD_RADIUS", "SPREAD_RING_STEP", "PER_RING", "calculateIconOffset"):
        assert removed not in content, f"{removed!r} should have been removed with the spread behavior"


def test_static_cluster_threshold_is_gone():
    # Clustering is no longer a fixed group-size rule evaluated once at load --
    # markercluster decides per zoom level, by screen distance.
    content = _content()
    assert "CLUSTER_MIN_SIZE" not in content
    assert "entries.length >= " not in content


def test_markers_are_handed_to_a_marker_cluster_group():
    content = _content()
    assert "L.markerClusterGroup(" in content
    assert "iconCreateFunction" in content
    assert "clusterGroup.addLayers(" in content


def test_cluster_radius_is_the_marker_width_so_pins_split_when_they_stop_overlapping():
    content = _content()
    assert "maxClusterRadius: MARKER_SIZE" in content


def test_markercluster_assets_are_vendored_and_loaded_after_leaflet():
    assert (MARKERCLUSTER_DIR / "leaflet.markercluster.js").exists()
    assert (MARKERCLUSTER_DIR / "MarkerCluster.css").exists()
    assert (MARKERCLUSTER_DIR / "LICENSE").exists()
    template = CARTE_TEMPLATE.read_text(encoding="utf-8")
    leaflet_at = template.index("vendor/leaflet/leaflet.js")
    markercluster_at = template.index("vendor/leaflet.markercluster/leaflet.markercluster.js")
    map_init_at = template.index("js/map_init.js")
    assert leaflet_at < markercluster_at < map_init_at
    assert "vendor/leaflet.markercluster/MarkerCluster.css" in template


def test_colocated_entries_are_spread_onto_a_ring_so_zooming_can_separate_them():
    # Identical coordinates stay identical at every zoom, so markercluster alone would
    # never split a household -- the ring is what makes "zoom in to separate" possible.
    content = _content()
    assert "function spreadEntries(" in content
    # Spacing is expressed in screen pixels at a chosen split zoom and converted to
    # ground units, because markercluster splits by screen distance. Stated directly
    # in ground units, the number moves the split zoom the opposite way from what the
    # value suggests (#126).
    assert re.search(r"const COLOCATED_SPLIT_ZOOM\s*=\s*\d+", content)
    assert re.search(r"const COLOCATED_SPACING_PX\s*=\s*MARKER_SIZE", content)
    assert "COLOCATED_SPACING_PX * metresPerPixel(group.lat, COLOCATED_SPLIT_ZOOM)" in content
    # Radius solves 2*r*sin(pi/n) = spacing, so neighbours stay a fixed distance apart
    # however large the group is.
    assert "spacingM / (2 * Math.sin(Math.PI / count))" in content


def test_ring_placement_is_deterministic_so_reloads_do_not_reshuffle_people():
    content = _content()
    assert "Math.random" not in content
    assert "(2 * Math.PI * index) / count" in content


def test_solo_entries_stay_exactly_on_their_true_coordinates():
    # The server contract (map_data.py) is untouched: only genuinely co-located
    # entries are displaced, and only for display.
    content = _content()
    assert "spread.push({ lat: group.lat, lon: group.lon, entry: group.entries[0] });" in content


def test_longitude_offset_accounts_for_latitude():
    # A degree of longitude shrinks with cos(latitude); ignoring it would stretch the
    # ring into an ellipse and change the spacing the whole design depends on.
    content = _content()
    assert "Math.cos((group.lat * Math.PI) / 180)" in content


def test_cluster_badge_shows_the_real_count_not_a_plus_n_remainder():
    # Three avatars are decoration; "+6" next to them read as "6 more" (i.e. 9 people).
    content = _content()
    assert "badge.textContent = String(entries.length);" in content
    assert "`+${" not in content
    assert "map-marker-cluster-badge" in content


def test_person_and_cluster_icons_share_the_same_geometry_helper():
    # With the spread offset gone, a solo icon and a cluster icon are geometrically
    # identical -- one shared factory, not two divergent ones.
    content = _content()
    assert "function buildMarkerIcon(" in content
    assert content.count("buildMarkerIcon(") >= 3  # definition + both call sites


def test_marker_size_is_a_single_constant_published_to_css():
    # Single source of truth (#85): JS and CSS must agree on marker size via
    # one shared custom property, not two independently-maintained numbers.
    content = _content()
    assert re.search(r"const MARKER_SIZE\s*=\s*\d+", content)
    assert "setProperty('--map-marker-size'" in content

    css_content = (STATIC_DIR / "css" / "main.css").read_text(encoding="utf-8")
    assert "var(--map-marker-size" in css_content


def test_icon_sizes_derive_from_marker_size_not_hardcoded():
    content = _content()
    assert "iconSize: [MARKER_SIZE, MARKER_SIZE]" in content
    assert "iconSize: [40, 40]" not in content


def test_fit_bounds_counts_unique_group_points_not_flat_markers():
    content = _content()
    assert "uniquePointCount" in content
    assert "allMarkers.length === 1" not in content


def test_search_index_is_built_from_one_marker_per_person():
    content = _content()
    assert "_entry" in content
    # Guards against reverting to the old per-group indexes.
    assert "_entries" not in content
    assert "_entryName" not in content
    assert "_groupIdx" not in content


def test_both_persons_and_chalets_cluster_with_their_own_label():
    # #114 (user decision): chalets cluster too, not persons-only -- one shared
    # buildClusterGroup() for both collections.
    content = _content()
    assert "buildClusterGroup(persons, 'membres')" in content
    assert "buildClusterGroup(chalets, 'chalets')" in content


def test_marker_avatar_carries_alt_text():
    content = _content()
    assert "img.alt = entryName || ''" in content


def test_search_zooms_until_the_person_leaves_their_cluster_then_opens_their_own_popup():
    # Every person has their own marker now, so a search no longer has to settle for
    # bolding a name inside a shared cluster popup.
    content = _content()
    assert "zoomToShowLayer(result.marker" in content
    assert "result.marker.openPopup()" in content


def test_clicking_a_cluster_lists_its_members_instead_of_zooming_to_bounds():
    # Reaching a profile from a zoomed-out view must stay a single click, as it was
    # before markercluster.
    content = _content()
    assert "zoomToBoundsOnClick: false" in content
    assert "clusterGroup.on('clusterclick'" in content
    assert "buildClusterPopup(entries, label)" in content
