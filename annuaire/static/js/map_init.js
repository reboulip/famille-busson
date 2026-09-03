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

    // Co-located groups of this size or more get the composite "+N" cluster pin
    // instead of their own individual markers -- previously only groups larger than
    // 8 clustered, and smaller ones spread into a ring of markers around the shared
    // point. A ring is unreadable even at 2-3 markers when they're this close
    // together, so every co-located group of 2+ now clusters (#114).
    const CLUSTER_MIN_SIZE = 2;

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

    // Shared L.divIcon geometry -- identical for a solo-person icon and a
    // composite cluster icon now that neither carries a spread offset.
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

    // Single-entry marker, exactly at the group's true lat/lon.
    function buildPersonIcon(entry) {
        return buildMarkerIcon(buildAvatarElement(entry.avatar, entry.name));
    }

    // Composite "+N" cluster pin for any co-located group of CLUSTER_MIN_SIZE or more.
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
        return buildMarkerIcon(cluster);
    }

    function buildEntryLink(entry) {
        const link = document.createElement('a');
        link.href = entry.url;
        link.textContent = entry.name;
        return link;
    }

    // Cluster-pin popup: heading + full list. `label` is the plural noun for the
    // heading ("membres" for persons, "chalets" for chalets) -- both collections
    // share this same cluster/popup code (#114), so the heading text can't be
    // hardcoded to one of them.
    function buildClusterPopup(group, label) {
        const wrapper = document.createElement('div');
        const heading = document.createElement('p');
        heading.className = 'map-marker-cluster-heading';
        heading.textContent = `${group.entries.length} ${label} à cette adresse`;
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

    // Builds a flat marker list from co-location groups: one marker per group,
    // always exactly at the group's point -- a composite cluster pin for groups of
    // CLUSTER_MIN_SIZE or more, a plain avatar pin for a solo entry (#114). Every
    // marker carries its group's full entries array as `_entries`, used below to
    // fix up the person search index now that groups no longer map 1:1 to markers
    // for multi-entry addresses.
    function buildMarkers(groups, label) {
        return groups.map((group) => {
            const entries = group.entries;
            const isCluster = entries.length >= CLUSTER_MIN_SIZE;
            const marker = L.marker([group.lat, group.lon], {
                icon: isCluster ? buildClusterIcon(group) : buildPersonIcon(entries[0]),
            });
            marker.bindPopup(isCluster ? buildClusterPopup(group, label) : buildEntryLink(entries[0]));
            marker._entries = entries;
            return marker;
        });
    }

    const personMarkers = buildMarkers(persons, 'membres');
    const chaletMarkers = buildMarkers(chalets, 'chalets');

    const personsLayer = L.layerGroup(personMarkers).addTo(map);
    const chaletsLayer = L.layerGroup(chaletMarkers).addTo(map);
    L.control.layers(null, { Membres: personsLayer, Chalets: chaletsLayer }).addTo(map);

    const allMarkers = personMarkers.concat(chaletMarkers);
    // Count distinct group points, not markers/collections -- a person and a
    // chalet can share the exact same coordinates (two separate arrays, two
    // markers), which would wrongly skip the single-point branch below and hit
    // fitBounds on a zero-area box, which zooms to max.
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

    // A solo entry's marker opens straight to their own popup; entries folded
    // into a cluster (CLUSTER_MIN_SIZE+) share their group's cluster marker/popup --
    // selectResult() below bolds the matched name in that shared list.
    const searchIndex = [];
    personMarkers.forEach((marker) => {
        marker._entries.forEach((entry) => searchIndex.push({ name: entry.name, marker }));
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

        // A cluster popup now lists every co-located person (#114), where it used
        // to open straight to the searched person's own marker -- bold their name
        // in the list so the search result is still easy to pick out.
        function highlightResultInPopup(result) {
            const popup = result.marker.getPopup();
            const content = popup ? popup.getContent() : null;
            if (!content || !content.querySelectorAll) return;
            content.querySelectorAll('.map-marker-cluster-list li').forEach((item) => {
                item.classList.toggle('fw-bold', item.textContent.trim() === result.name);
            });
        }

        function selectResult(result) {
            if (!map.hasLayer(personsLayer)) {
                map.addLayer(personsLayer);
            }
            map.setView(result.marker.getLatLng(), 15);
            result.marker.openPopup();
            highlightResultInPopup(result);
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
