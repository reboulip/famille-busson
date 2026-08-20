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

    function buildPopup(person) {
        const link = document.createElement('a');
        link.href = person.url;
        link.textContent = person.name;
        return link;
    }

    const markers = persons.map((person) => {
        const marker = L.marker([person.lat, person.lon]).addTo(map);
        marker.bindPopup(buildPopup(person));
        return marker;
    });

    if (markers.length === 1) {
        map.setView(markers[0].getLatLng(), 13);
    } else {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.2));
    }
});
