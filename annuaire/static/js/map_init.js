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

    function buildAvatarElement(avatarUrl) {
        const avatar = document.createElement('div');
        avatar.className = 'map-marker-avatar';
        if (avatarUrl.startsWith(EMOJI_PREFIX)) {
            avatar.classList.add('map-marker-avatar-emoji');
            avatar.textContent = avatarUrl.slice(EMOJI_PREFIX.length);
        } else {
            const img = document.createElement('img');
            img.src = avatarUrl;
            img.alt = '';
            avatar.appendChild(img);
        }
        return avatar;
    }

    function buildGroupIcon(group) {
        if (group.entries.length === 1) {
            return L.divIcon({
                className: 'map-marker-avatar-wrapper',
                html: buildAvatarElement(group.entries[0].avatar),
                iconSize: [40, 40],
                iconAnchor: [20, 40],
                popupAnchor: [0, -40],
            });
        }
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
        return L.divIcon({
            className: 'map-marker-avatar-wrapper',
            html: cluster,
            iconSize: [40, 40],
            iconAnchor: [20, 40],
            popupAnchor: [0, -40],
        });
    }

    function buildEntryLink(entry) {
        const link = document.createElement('a');
        link.href = entry.url;
        link.textContent = entry.name;
        return link;
    }

    function buildGroupPopup(group) {
        if (group.entries.length === 1) {
            return buildEntryLink(group.entries[0]);
        }
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

    function buildMarkers(groups) {
        return groups.map((group) => {
            const marker = L.marker([group.lat, group.lon], { icon: buildGroupIcon(group) });
            marker.bindPopup(buildGroupPopup(group));
            return marker;
        });
    }

    const personMarkers = buildMarkers(persons);
    const chaletMarkers = buildMarkers(chalets);

    const personsLayer = L.layerGroup(personMarkers).addTo(map);
    const chaletsLayer = L.layerGroup(chaletMarkers).addTo(map);
    L.control.layers(null, { Membres: personsLayer, Chalets: chaletsLayer }).addTo(map);

    const allMarkers = personMarkers.concat(chaletMarkers);
    if (allMarkers.length === 1) {
        map.setView(allMarkers[0].getLatLng(), 13);
    } else {
        const group = L.featureGroup(allMarkers);
        map.fitBounds(group.getBounds().pad(0.2));
    }
});
