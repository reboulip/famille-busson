(function () {
    function parseISODate(s) {
        if (!s) return null;
        const [y, m, d] = s.split('-').map(Number);
        if (!y) return null;
        return new Date(y, m - 1, d);
    }
    function midnight(d) {
        const x = new Date(d);
        x.setHours(0, 0, 0, 0);
        return x;
    }
    function addDays(d, n) {
        const x = new Date(d);
        x.setDate(x.getDate() + n);
        return x;
    }
    function addMonths(d, n) {
        const x = new Date(d);
        x.setMonth(x.getMonth() + n);
        return x;
    }
    function dayDiff(a, b) {
        return Math.round((b - a) / 86400000);
    }
    function sameDay(a, b) {
        return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
    }
    function formatDayHeader(d, mode) {
        if (mode === 'long') {
            if (d.getDate() === 1) {
                return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
            }
            return d.getDate() % 5 === 0 ? String(d.getDate()) : '';
        }
        const weekday = d.toLocaleDateString('fr-FR', { weekday: 'short' })[0].toUpperCase();
        return `${weekday}\n${d.getDate()}`;
    }
    function formatDate(d) {
        return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
    }

    // Wires the shared toolbar controls (.cal-prev/.cal-next/.cal-today/.cal-window-toggle)
    // on `root` to caller-supplied callbacks. Used by both presence_calendar.js
    // (Gantt/timeline) and unified_calendar.js (month/agenda) so navigation behaves
    // identically across both renderers.
    function initNavigation(root, { onPrev, onNext, onToday, onWindowChange } = {}) {
        root.querySelectorAll('.cal-prev').forEach((btn) => btn.addEventListener('click', () => onPrev && onPrev()));
        root.querySelectorAll('.cal-next').forEach((btn) => btn.addEventListener('click', () => onNext && onNext()));
        root.querySelectorAll('.cal-today').forEach((btn) => btn.addEventListener('click', () => onToday && onToday()));
        root.querySelectorAll('.cal-window-toggle').forEach((btn) => {
            btn.addEventListener('click', () => {
                root.querySelectorAll('.cal-window-toggle').forEach((b) => b.classList.toggle('active', b === btn));
                if (onWindowChange) onWindowChange(btn.dataset.target);
            });
        });
    }

    window.FBCalendar = {
        parseISODate,
        midnight,
        addDays,
        addMonths,
        dayDiff,
        sameDay,
        formatDayHeader,
        formatDate,
        initNavigation,
    };
})();
