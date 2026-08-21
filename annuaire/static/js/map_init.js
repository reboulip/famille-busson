document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('carte-map');
    if (!container) return;

    const persons = JSON.parse(container.dataset.persons || '[]');

    // Metropolitan France, zoomed out -- sensible default when there's nothing to fit to.
    const map = L.map(container).setView([46.6, 2.4], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    if (persons.length === 0) {
        return;
    }

    function buildAvatarIcon(avatarUrl) {
        const avatar = document.createElement('div');
        avatar.className = 'map-marker-avatar';
        const img = document.createElement('img');
        img.src = avatarUrl;
        img.alt = '';
        avatar.appendChild(img);
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
            const marker = L.marker([entry.lat, entry.lon], { icon: buildAvatarIcon(entry.avatar) }).addTo(map);
            marker.bindPopup(buildPopup(entry));
            return marker;
        });
    }

    const markers = buildMarkers(persons);

    if (markers.length === 1) {
        map.setView(markers[0].getLatLng(), 13);
    } else {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.2));
    }
});
