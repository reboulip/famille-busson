(function () {
    const { parseISODate, midnight, sameDay, formatDate, initNavigation } = window.FBCalendar;

    const TYPE_LABELS = { event: 'Événement', presence: 'Présence', birthday: 'Anniversaire' };

    const roots = document.querySelectorAll('.unified-calendar');
    roots.forEach(initUnifiedCalendar);

    function initUnifiedCalendar(root) {
        const monthGrid = root.querySelector('.unified-calendar-month');
        const agenda = root.querySelector('.unified-calendar-agenda');
        const rangeLabel = root.querySelector('.unified-calendar-range');
        const feedUrl = root.dataset.feedUrl;
        if (!monthGrid || !agenda) return;

        function isoDate(d) {
            return d.toISOString().slice(0, 10);
        }

        function normalizeEntry(e) {
            return Object.assign({}, e, {
                startDate: parseISODate(e.start.slice(0, 10)),
                endDate: parseISODate(e.end.slice(0, 10)),
            });
        }

        let entries;
        try {
            entries = JSON.parse(root.dataset.entries || '[]');
        } catch (e) {
            entries = [];
        }
        entries = entries.map(normalizeEntry);

        let loadedStart = parseISODate(root.dataset.windowStart);
        let loadedEnd = parseISODate(root.dataset.windowEnd);
        const activeTypes = new Set((root.dataset.activeTypes || '').split(',').filter(Boolean));
        let anchor = midnight(new Date());

        root.querySelectorAll('.cal-filter-chip').forEach((chip) => {
            chip.classList.toggle('active', activeTypes.has(chip.dataset.type));
            chip.addEventListener('click', () => {
                if (activeTypes.has(chip.dataset.type)) {
                    activeTypes.delete(chip.dataset.type);
                } else {
                    activeTypes.add(chip.dataset.type);
                }
                chip.classList.toggle('active');
                render();
            });
        });

        initNavigation(root, {
            onPrev: () => {
                anchor = new Date(anchor.getFullYear(), anchor.getMonth() - 1, 1);
                navigate();
            },
            onNext: () => {
                anchor = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 1);
                navigate();
            },
            onToday: () => {
                anchor = midnight(new Date());
                navigate();
            },
        });

        function navigate() {
            const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
            const monthEnd = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);
            if (monthStart >= loadedStart && monthEnd <= loadedEnd) {
                render();
                return;
            }
            const fetchStart = monthStart < loadedStart ? monthStart : loadedStart;
            const fetchEnd = monthEnd > loadedEnd ? monthEnd : loadedEnd;
            const params = new URLSearchParams({
                start: isoDate(fetchStart),
                end: isoDate(fetchEnd),
                types: Array.from(activeTypes).join(','),
            });
            fetch(feedUrl + '?' + params.toString())
                .then((r) => r.json())
                .then((data) => {
                    entries = (data.entries || []).map(normalizeEntry);
                    loadedStart = fetchStart;
                    loadedEnd = fetchEnd;
                    render();
                });
        }

        function render() {
            const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
            const monthEnd = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);
            const visible = entries.filter(
                (e) => activeTypes.has(e.type) && e.endDate >= monthStart && e.startDate <= monthEnd
            );

            renderMonthGrid(monthStart, monthEnd, visible);
            renderAgenda(visible);

            if (rangeLabel) {
                rangeLabel.textContent = anchor.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
            }
        }

        function renderMonthGrid(monthStart, monthEnd, visible) {
            monthGrid.innerHTML = '';
            const firstWeekday = (monthStart.getDay() + 6) % 7; // Monday-first
            const daysInMonth = monthEnd.getDate();
            const today = midnight(new Date());

            for (let i = 0; i < firstWeekday; i++) {
                const filler = document.createElement('div');
                filler.className = 'cal-month-cell cal-month-cell--empty';
                monthGrid.appendChild(filler);
            }
            for (let day = 1; day <= daysInMonth; day++) {
                const d = new Date(monthStart.getFullYear(), monthStart.getMonth(), day);
                const cell = document.createElement('div');
                cell.className = 'cal-month-cell';
                if (sameDay(d, today)) cell.classList.add('cal-month-cell--today');

                const label = document.createElement('span');
                label.className = 'cal-month-cell__day';
                label.textContent = String(day);
                cell.appendChild(label);

                const dots = document.createElement('div');
                dots.className = 'cal-month-cell__dots';
                const dayTypes = new Set(visible.filter((e) => e.startDate <= d && e.endDate >= d).map((e) => e.type));
                dayTypes.forEach((type) => {
                    const dot = document.createElement('span');
                    dot.className = 'cal-dot cal-type-' + type;
                    dots.appendChild(dot);
                });
                cell.appendChild(dots);
                monthGrid.appendChild(cell);
            }
        }

        function renderAgenda(visible) {
            agenda.innerHTML = '';
            const sorted = visible.slice().sort((a, b) => a.startDate - b.startDate);
            if (sorted.length === 0) {
                const empty = document.createElement('p');
                empty.className = 'fb-meta';
                empty.textContent = 'Rien de prévu ce mois-ci.';
                agenda.appendChild(empty);
                return;
            }
            sorted.forEach((e) => {
                const item = document.createElement('a');
                item.className = 'cal-agenda-item';
                item.href = e.url || '#';

                const badge = document.createElement('span');
                badge.className = 'cal-chip cal-type-' + e.type;
                badge.textContent = TYPE_LABELS[e.type] || e.type;
                item.appendChild(badge);

                const title = document.createElement('span');
                title.className = 'cal-agenda-item__title';
                title.textContent = e.title + (e.subtitle ? ' · ' + e.subtitle : '');
                item.appendChild(title);

                const date = document.createElement('span');
                date.className = 'fb-meta';
                date.textContent = formatDate(e.startDate);
                item.appendChild(date);

                agenda.appendChild(item);
            });
        }

        render();
    }
})();
