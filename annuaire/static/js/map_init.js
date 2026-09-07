document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('carte-map');
    if (!container) return;

    const persons = JSON.parse(container.dataset.persons || '[]');
    const chalets = JSON.parse(container.dataset.chalets || '[]');
    const events = JSON.parse(container.dataset.events || '[]');

    // Metropolitan France, zoomed out -- sensible default when there's nothing to fit to.
    const map = L.map(container).setView([46.6, 2.4], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    if (persons.length === 0 && chalets.length === 0 && events.length === 0) {
        return;
    }

    // Chalets without a photo carry a "placeholder::<kind>" sentinel instead of an image
    // URL (there's no default chalet photo asset the way there is a default person
    // avatar). See annuaire/map_data.py's PLACEHOLDER_PREFIX -- keep the two in sync.
    const PLACEHOLDER_PREFIX = 'placeholder::';

    // The ridge mark, inline. Same silhouette as annuaire/templates/annuaire/_ridge.html
    // and favicon.svg; drawn rather than written as an emoji so it never renders as a
    // tofu box and so it follows Alpenglow/Nightfall through the CSS custom properties.
    const RIDGE_SVG =
        '<svg class="fb-ridge" viewBox="0 0 240 76" preserveAspectRatio="none" aria-hidden="true">' +
        '<path class="fb-ridge__far" d="M0,76 L26,42 L52,58 L82,30 L108,56 L140,36 L172,60 L200,44 L240,62 L240,76 Z"/>' +
        '<path class="fb-ridge__near" d="M0,76 L38,26 L66,54 L100,10 L136,50 L168,30 L206,58 L240,38 L240,76 Z"/>' +
        '<path class="fb-ridge__snow" d="M100,10 L112,24 L106,21 L100,28 L94,21 L88,24 Z"/>' +
        '</svg>';

    // Event markers get a calendar glyph instead of the ridge. Path data
    // duplicated from annuaire/templatetags/icons.py's "calendar" entry --
    // client-side JS has no access to the {% icon %} templatetag at render
    // time. Keep the two in sync.
    const EVENT_SVG =
        '<svg class="fb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M4 5.5h16v14H4z"/><path d="M4 9.5h16"/><path d="M8 3v4"/><path d="M16 3v4"/>' +
        '</svg>';

    // Single source of truth for marker medallion size (60 = 40 * 1.5), published
    // as a CSS custom property so main.css's .map-marker-* rules stay in sync
    // (mirrors family_tree.js's --genealogie-label-max-width precedent).
    const MARKER_SIZE = 60;
    document.documentElement.style.setProperty('--map-marker-size', `${MARKER_SIZE}px`);

    // Where a co-located group separates, and how close its pins sit when it does
    // (see spreadEntries). markercluster splits by *screen* distance, so the ring is
    // sized in pixels at a chosen zoom and only then converted to ground metres.
    // Sizing it in ground metres directly is what used to push the split out to
    // maximum zoom: a fixed ground distance shrinks on screen as you zoom out, so
    // lowering that number raises the split zoom instead of lowering it.
    const COLOCATED_SPLIT_ZOOM = 17;
    const COLOCATED_SPACING_PX = MARKER_SIZE + 6;
    const EQUATOR_M = 40075016.686;
    const METRES_PER_DEGREE_LAT = 111320;

    // Web Mercator ground resolution: metres covered by one screen pixel.
    function metresPerPixel(latitude, zoom) {
        return (EQUATOR_M * Math.cos((latitude * Math.PI) / 180)) / 2 ** (zoom + 8);
    }

    function buildAvatarElement(avatarUrl, entryName) {
        const avatar = document.createElement('div');
        avatar.className = 'map-marker-avatar';
        if (avatarUrl.startsWith(PLACEHOLDER_PREFIX)) {
            avatar.classList.add('map-marker-avatar-placeholder');
            const suffix = avatarUrl.slice(PLACEHOLDER_PREFIX.length);
            if (suffix === 'event') {
                avatar.classList.add('map-marker-avatar-event');
                avatar.innerHTML = EVENT_SVG;
            } else {
                avatar.innerHTML = RIDGE_SVG;
            }
        } else {
            const img = document.createElement('img');
            img.src = avatarUrl;
            img.alt = entryName || '';
            avatar.appendChild(img);
        }
        return avatar;
    }

    // Shared L.divIcon geometry -- identical for a solo-person icon and a
    // composite cluster icon.
    function buildMarkerIcon(htmlNode) {
        const half = MARKER_SIZE / 2;
        return L.divIcon({
            className: 'map-marker-avatar-wrapper',
            html: htmlNode,
            iconSize: [MARKER_SIZE, MARKER_SIZE],
            iconAnchor: [half, MARKER_SIZE],
            popupAnchor: [0, -MARKER_SIZE],
        });
    }

    function buildPersonIcon(entry) {
        return buildMarkerIcon(buildAvatarElement(entry.avatar, entry.name));
    }

    // Composite pin for a cluster of overlapping markers: up to three stacked
    // avatars plus the total count. The badge is the cluster's real size, not a
    // "+N" remainder -- three avatars are decoration, not a partial listing (#114).
    function buildClusterIcon(entries) {
        const cluster = document.createElement('div');
        cluster.className = 'map-marker-cluster';
        entries.slice(0, 3).forEach((entry) => {
            const avatar = buildAvatarElement(entry.avatar);
            avatar.classList.add('map-marker-cluster-avatar');
            cluster.appendChild(avatar);
        });
        const badge = document.createElement('div');
        badge.className = 'map-marker-cluster-badge';
        badge.textContent = String(entries.length);
        cluster.appendChild(badge);
        return buildMarkerIcon(cluster);
    }

    function buildEntryLink(entry) {
        const link = document.createElement('a');
        link.href = entry.url;
        link.textContent = entry.name;
        return link;
    }

    // Cluster popup: heading + full list. `label` is the plural noun for the heading
    // ("membres" for persons, "chalets" for chalets) -- both collections share this
    // code. A cluster is now a *screen-space* grouping (Leaflet.markercluster), so it
    // can span neighbouring addresses, not just one: hence "à proximité", not
    // "à cette adresse".
    function buildClusterPopup(entries, label) {
        const wrapper = document.createElement('div');
        const heading = document.createElement('p');
        heading.className = 'map-marker-cluster-heading';
        heading.textContent = `${entries.length} ${label} à proximité`;
        wrapper.appendChild(heading);
        const list = document.createElement('ul');
        list.className = 'map-marker-cluster-list';
        entries.forEach((entry) => {
            const item = document.createElement('li');
            item.appendChild(buildEntryLink(entry));
            list.appendChild(item);
        });
        wrapper.appendChild(list);
        return wrapper;
    }

    // Everyone at one address shares the exact same coordinates, so no amount of
    // zooming would ever pull their markers apart -- Leaflet.markercluster splits
    // clusters by screen distance, and that distance stays zero. Spread each
    // co-located group onto a small ring around its true point (display only; the
    // stored coordinates are untouched) so zooming in eventually separates them.
    // The radius grows with the group size to keep neighbours a fixed distance
    // apart: n points on a ring of radius r sit 2*r*sin(pi/n) apart. (#114)
    function spreadEntries(groups) {
        const spread = [];
        groups.forEach((group) => {
            const count = group.entries.length;
            if (count === 1) {
                spread.push({ lat: group.lat, lon: group.lon, entry: group.entries[0] });
                return;
            }
            // Ground spacing that renders as COLOCATED_SPACING_PX at the split zoom.
            // The ring is fixed in ground units, so pins keep spreading apart as you
            // zoom past that point -- deliberate, and cheaper than re-spreading on
            // every zoom, which would fight zoomToShowLayer and the initial fitBounds.
            const spacingM = COLOCATED_SPACING_PX * metresPerPixel(group.lat, COLOCATED_SPLIT_ZOOM);
            const radius = spacingM / (2 * Math.sin(Math.PI / count));
            const metresPerDegreeLon = METRES_PER_DEGREE_LAT * Math.cos((group.lat * Math.PI) / 180);
            group.entries.forEach((entry, index) => {
                // Start at the top and go clockwise -- deterministic, so a reload
                // never reshuffles who sits where.
                const angle = (2 * Math.PI * index) / count - Math.PI / 2;
                spread.push({
                    lat: group.lat + (radius * Math.sin(angle)) / METRES_PER_DEGREE_LAT,
                    lon: group.lon + (radius * Math.cos(angle)) / (metresPerDegreeLon || METRES_PER_DEGREE_LAT),
                    entry,
                });
            });
        });
        return spread;
    }

    // One marker per entry, handed to a markerClusterGroup that merges/splits them
    // by screen distance as the zoom changes. maxClusterRadius is the medallion
    // width, so pins separate exactly when they stop overlapping.
    function buildClusterGroup(groups, label) {
        const clusterGroup = L.markerClusterGroup({
            maxClusterRadius: MARKER_SIZE,
            showCoverageOnHover: false,
            // Click opens the member list (as it did before markercluster) instead of
            // zooming to bounds -- reaching a profile from a zoomed-out view stays a
            // single click. Zooming still splits clusters through the normal controls.
            zoomToBoundsOnClick: false,
            // spreadEntries() guarantees co-located pins separate before max zoom, so
            // the spider-leg fallback would only ever fire for genuinely distinct
            // addresses a metre apart -- the popup lists those just as well.
            spiderfyOnMaxZoom: false,
            iconCreateFunction: (cluster) => buildClusterIcon(cluster.getAllChildMarkers().map((m) => m._entry)),
        });
        const markers = spreadEntries(groups).map((placed) => {
            const marker = L.marker([placed.lat, placed.lon], { icon: buildPersonIcon(placed.entry) });
            marker.bindPopup(buildEntryLink(placed.entry));
            marker._entry = placed.entry;
            return marker;
        });
        clusterGroup.addLayers(markers);
        clusterGroup.on('clusterclick', (event) => {
            const entries = event.layer.getAllChildMarkers().map((m) => m._entry);
            L.popup({ offset: [0, -MARKER_SIZE] })
                .setLatLng(event.layer.getLatLng())
                .setContent(buildClusterPopup(entries, label))
                .openOn(map);
        });
        return { clusterGroup, markers };
    }

    const personsLayer = buildClusterGroup(persons, 'membres');
    const chaletsLayer = buildClusterGroup(chalets, 'chalets');
    const eventsLayer = buildClusterGroup(events, 'événements');
    map.addLayer(personsLayer.clusterGroup);
    map.addLayer(chaletsLayer.clusterGroup);
    map.addLayer(eventsLayer.clusterGroup);
    L.control
        .layers(null, {
            Membres: personsLayer.clusterGroup,
            Chalets: chaletsLayer.clusterGroup,
            Événements: eventsLayer.clusterGroup,
        })
        .addTo(map);

    const allMarkers = personsLayer.markers.concat(chaletsLayer.markers).concat(eventsLayer.markers);
    // Count distinct group points, not markers/collections -- a person, a
    // chalet and an event can share the exact same coordinates (separate
    // arrays, separate markers), which would wrongly skip the single-point
    // branch below and hit fitBounds on a zero-area box, which zooms to max.
    const uniquePointCount = new Set(persons.concat(chalets).concat(events).map((g) => `${g.lat},${g.lon}`)).size;
    if (uniquePointCount === 1) {
        map.setView(allMarkers[0].getLatLng(), 13);
    } else {
        map.fitBounds(L.featureGroup(allMarkers).getBounds().pad(0.2));
    }

    // Client-side search over the members already plotted on the map (accent-
    // insensitive, unlike the accent-sensitive server-side directory search on
    // SQLite -- deliberate, since this search has no server round-trip to pay for).
    function normalizeForSearch(str) {
        return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
    }

    // Every person now has their own marker, whether or not it is currently folded
    // into a cluster -- zoomToShowLayer() below zooms until it is separated out,
    // then opens that person's own popup.
    const searchIndex = personsLayer.markers.map((marker) => ({ name: marker._entry.name, marker }));

    initPersonSearch();

    function initPersonSearch() {
        const input = document.getElementById('carte-person-search');
        const resultsList = document.getElementById('carte-person-search-results');
        if (!input || !resultsList) return;

        let highlightedIndex = -1;
        let debounceTimer = null;

        function closeDropdown() {
            resultsList.innerHTML = '';
            resultsList.hidden = true;
            highlightedIndex = -1;
        }

        function updateHighlight() {
            const items = resultsList.querySelectorAll('.person-picker-result');
            items.forEach((el, idx) => el.classList.toggle('highlighted', idx === highlightedIndex));
        }

        function selectResult(result) {
            if (!map.hasLayer(personsLayer.clusterGroup)) {
                map.addLayer(personsLayer.clusterGroup);
            }
            // Zoom in far enough for the marker to leave its cluster, then open it --
            // openPopup() on a still-clustered marker would silently do nothing.
            personsLayer.clusterGroup.zoomToShowLayer(result.marker, () => result.marker.openPopup());
            closeDropdown();
            input.value = '';
        }

        function renderResults(results) {
            resultsList.innerHTML = '';
            if (results.length === 0) {
                const li = document.createElement('li');
                li.className = 'person-picker-empty';
                li.textContent = 'Aucun membre trouvé';
                resultsList.appendChild(li);
                resultsList.hidden = false;
                highlightedIndex = -1;
                return;
            }
            results.forEach((result) => {
                const li = document.createElement('li');
                li.className = 'person-picker-result';
                li.setAttribute('role', 'option');
                li.textContent = result.name;
                li.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    selectResult(result);
                });
                resultsList.appendChild(li);
            });
            resultsList.hidden = false;
            highlightedIndex = 0;
            updateHighlight();
        }

        function search(query) {
            const normalizedQuery = normalizeForSearch(query);
            const results = searchIndex.filter((entry) => normalizeForSearch(entry.name).includes(normalizedQuery));
            renderResults(results);
        }

        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const q = input.value.trim();
            if (q.length < 2) {
                closeDropdown();
                return;
            }
            debounceTimer = setTimeout(() => search(q), 250);
        });

        input.addEventListener('keydown', (e) => {
            const items = resultsList.querySelectorAll('.person-picker-result');
            if (e.key === 'ArrowDown') {
                if (items.length === 0) return;
                e.preventDefault();
                highlightedIndex = (highlightedIndex + 1) % items.length;
                updateHighlight();
            } else if (e.key === 'ArrowUp') {
                if (items.length === 0) return;
                e.preventDefault();
                highlightedIndex = (highlightedIndex - 1 + items.length) % items.length;
                updateHighlight();
            } else if (e.key === 'Enter') {
                if (highlightedIndex >= 0 && items[highlightedIndex]) {
                    e.preventDefault();
                    const query = normalizeForSearch(input.value.trim());
                    const result = searchIndex.filter((entry) => normalizeForSearch(entry.name).includes(query))[
                        highlightedIndex
                    ];
                    if (result) selectResult(result);
                }
            } else if (e.key === 'Escape') {
                closeDropdown();
            }
        });

        document.addEventListener('click', (e) => {
            if (e.target !== input && !resultsList.contains(e.target)) closeDropdown();
        });
    }
});
