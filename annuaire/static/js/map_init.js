document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('carte-map');
    if (!container) return;

    const persons = JSON.parse(container.dataset.persons || '[]');
    const chalets = JSON.parse(container.dataset.chalets || '[]');

    // Metropolitan France, zoomed out -- sensible default when there's nothing to fit to.
    const map = L.map(container).setView([46.6, 2.4], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    if (persons.length === 0 && chalets.length === 0) {
        return;
    }

    // Chalets without a photo carry an "emoji::<char>" sentinel instead of an image URL
    // (there's no default chalet photo asset the way there is a default person avatar).
    const EMOJI_PREFIX = 'emoji::';

    // Single source of truth for marker medallion size (60 = 40 * 1.5), published
    // as a CSS custom property so main.css's .map-marker-* rules stay in sync
    // (mirrors family_tree.js's --genealogie-label-max-width precedent).
    const MARKER_SIZE = 60;
    document.documentElement.style.setProperty('--map-marker-size', `${MARKER_SIZE}px`);

    // Co-located groups up to this size spread into individual markers arranged
    // around the shared point instead of one composite cluster pin; larger
    // groups keep the cluster pin below (a ring that big would be unreadable
    // and would swamp neighboring markers at low zoom).
    const SPREAD_MAX = 8;
    const SPREAD_RADIUS = 51; // px, first ring (1.5x MARKER_SIZE's 34px baseline)
    const SPREAD_RING_STEP = 39; // px added per additional ring (1.5x baseline)
    const PER_RING = 6; // markers per ring before overflowing to the next ring

    // Pixel offset for the i-th (of `total`) spread marker in a group, laid
    // out on concentric rings around the shared point -- varying distance
    // (ring) and angle so avatars don't overlap.
    function calculateIconOffset(index, total) {
        const ring = Math.floor(index / PER_RING);
        const indexInRing = index % PER_RING;
        const countInRing = Math.min(PER_RING, total - ring * PER_RING);
        const radius = SPREAD_RADIUS + ring * SPREAD_RING_STEP;
        // Stagger each ring's start angle so rings don't align radially.
        const angle = (2 * Math.PI * indexInRing) / countInRing + ring * (Math.PI / PER_RING);
        return {
            dx: Math.round(radius * Math.cos(angle)),
            dy: Math.round(radius * Math.sin(angle)),
        };
    }

    function buildAvatarElement(avatarUrl, entryName) {
        const avatar = document.createElement('div');
        avatar.className = 'map-marker-avatar';
        if (avatarUrl.startsWith(EMOJI_PREFIX)) {
            avatar.classList.add('map-marker-avatar-emoji');
            avatar.textContent = avatarUrl.slice(EMOJI_PREFIX.length);
        } else {
            const img = document.createElement('img');
            img.src = avatarUrl;
            img.alt = entryName || '';
            avatar.appendChild(img);
        }
        return avatar;
    }

    // Single-person marker, optionally shifted by a spread offset (in pixels).
    // The marker itself always stays at the group's true lat/lon -- only the
    // icon (and its popup anchor) move, via iconAnchor/popupAnchor, so
    // fitBounds/search/zoom all keep working against real coordinates.
    function buildPersonIcon(entry, offset) {
        const dx = offset ? offset.dx : 0;
        const dy = offset ? offset.dy : 0;
        const half = MARKER_SIZE / 2;
        return L.divIcon({
            className: 'map-marker-avatar-wrapper',
            html: buildAvatarElement(entry.avatar, entry.name),
            iconSize: [MARKER_SIZE, MARKER_SIZE],
            iconAnchor: [half - dx, MARKER_SIZE - dy],
            popupAnchor: [dx, dy - MARKER_SIZE],
        });
    }

    // Composite "+N" cluster pin for groups too large to spread legibly.
    function buildClusterIcon(group) {
        const cluster = document.createElement('div');
        cluster.className = 'map-marker-cluster';
        group.entries.slice(0, 3).forEach((entry) => {
            const avatar = buildAvatarElement(entry.avatar);
            avatar.classList.add('map-marker-cluster-avatar');
            cluster.appendChild(avatar);
        });
        const badge = document.createElement('div');
        badge.className = 'map-marker-cluster-badge';
        badge.textContent = `+${group.entries.length}`;
        cluster.appendChild(badge);
        const half = MARKER_SIZE / 2;
        return L.divIcon({
            className: 'map-marker-avatar-wrapper',
            html: cluster,
            iconSize: [MARKER_SIZE, MARKER_SIZE],
            iconAnchor: [half, MARKER_SIZE],
            popupAnchor: [0, -MARKER_SIZE],
        });
    }

    function buildEntryLink(entry) {
        const link = document.createElement('a');
        link.href = entry.url;
        link.textContent = entry.name;
        return link;
    }

    // Cluster-pin popup (groups too large to spread): heading + full list.
    function buildClusterPopup(group) {
        const wrapper = document.createElement('div');
        const heading = document.createElement('p');
        heading.className = 'map-marker-cluster-heading';
        heading.textContent = `${group.entries.length} membres à cette adresse`;
        wrapper.appendChild(heading);
        const list = document.createElement('ul');
        list.className = 'map-marker-cluster-list';
        group.entries.forEach((entry) => {
            const item = document.createElement('li');
            item.appendChild(buildEntryLink(entry));
            list.appendChild(item);
        });
        wrapper.appendChild(list);
        return wrapper;
    }

    // Builds a flat marker list from co-location groups. Groups of up to
    // SPREAD_MAX entries spread into one marker per entry (offset around the
    // shared point); larger groups keep a single composite cluster marker,
    // exactly at the group's point. Each marker carries metadata
    // (_groupIdx/_entryName or _entries) used below to fix up fitBounds and
    // the person search index now that groups no longer map 1:1 to markers.
    function buildMarkers(groups) {
        const markers = [];
        groups.forEach((group, groupIdx) => {
            const entries = group.entries;
            if (entries.length > SPREAD_MAX) {
                const marker = L.marker([group.lat, group.lon], { icon: buildClusterIcon(group) });
                marker.bindPopup(buildClusterPopup(group));
                marker._groupIdx = groupIdx;
                marker._entries = entries;
                markers.push(marker);
                return;
            }
            entries.forEach((entry, i) => {
                const offset = entries.length > 1 ? calculateIconOffset(i, entries.length) : null;
                const marker = L.marker([group.lat, group.lon], { icon: buildPersonIcon(entry, offset) });
                marker.bindPopup(buildEntryLink(entry));
                marker._groupIdx = groupIdx;
                marker._entryName = entry.name;
                markers.push(marker);
            });
        });
        return markers;
    }

    const personMarkers = buildMarkers(persons);
    const chaletMarkers = buildMarkers(chalets);

    const personsLayer = L.layerGroup(personMarkers).addTo(map);
    const chaletsLayer = L.layerGroup(chaletMarkers).addTo(map);
    L.control.layers(null, { Membres: personsLayer, Chalets: chaletsLayer }).addTo(map);

    const allMarkers = personMarkers.concat(chaletMarkers);
    // Spreading can turn one co-located group into several markers at the
    // *same* lat/lon -- count distinct group points, not markers, or a
    // spread group of e.g. 3 people would wrongly skip the single-point
    // branch and hit fitBounds on a zero-area box, which zooms to max.
    const uniquePointCount = new Set(persons.concat(chalets).map((g) => `${g.lat},${g.lon}`)).size;
    if (uniquePointCount === 1) {
        map.setView(allMarkers[0].getLatLng(), 13);
    } else {
        const group = L.featureGroup(allMarkers);
        map.fitBounds(group.getBounds().pad(0.2));
    }

    // Client-side search over the members already plotted on the map (accent-
    // insensitive, unlike the accent-sensitive server-side directory search on
    // SQLite -- deliberate, since this search has no server round-trip to pay for).
    function normalizeForSearch(str) {
        return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
    }

    // Spreading gives most entries their own marker (opens straight to that
    // person's popup); entries still folded into a cluster (>SPREAD_MAX) fall
    // back to opening the shared cluster marker/popup.
    const searchIndex = [];
    personMarkers.forEach((marker) => {
        if (marker._entryName) {
            searchIndex.push({ name: marker._entryName, marker });
        } else if (marker._entries) {
            marker._entries.forEach((entry) => searchIndex.push({ name: entry.name, marker }));
        }
    });

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
            if (!map.hasLayer(personsLayer)) {
                map.addLayer(personsLayer);
            }
            map.setView(result.marker.getLatLng(), 15);
            result.marker.openPopup();
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
