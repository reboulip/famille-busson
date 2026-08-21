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

    function buildAvatarIcon(avatarUrl) {
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
        return L.divIcon({
            className: 'map-marker-avatar-wrapper',
            html: avatar,
            iconSize: [40, 40],
            iconAnchor: [20, 40],
            popupAnchor: [0, -40],
        });
    }

    function buildPopup(entry) {
        const link = document.createElement('a');
        link.href = entry.url;
        link.textContent = entry.name;
        return link;
    }

    function buildMarkers(entries) {
        return entries.map((entry) => {
            const marker = L.marker([entry.lat, entry.lon], { icon: buildAvatarIcon(entry.avatar) });
            marker.bindPopup(buildPopup(entry));
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
