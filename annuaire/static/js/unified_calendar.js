(function () {
    const { parseISODate, midnight, sameDay, initNavigation } = window.FBCalendar;

    const TYPE_LABELS = {
        event: gettext('Événement'),
        presence: gettext('Présence'),
        birthday: gettext('Anniversaire'),
    };

    const roots = document.querySelectorAll('.unified-calendar');
    roots.forEach(initUnifiedCalendar);

    function initUnifiedCalendar(root) {
        const monthGrid = root.querySelector('.unified-calendar-month');
        const weekdaysEl = root.querySelector('.unified-calendar-weekdays');
        const agenda = root.querySelector('.unified-calendar-agenda');
        const rangeLabel = root.querySelector('.unified-calendar-range');
        const feedUrl = root.dataset.feedUrl;
        if (!monthGrid || !agenda) return;

        const lang = document.documentElement.lang || 'fr';

        // Build the date string from local Y/M/D -- toISOString() converts to
        // UTC first, which can shift local midnight to the previous day
        // (e.g. Europe/Paris local midnight -> 22:00 UTC the day before),
        // silently dropping the last day of a fetch window.
        function isoDate(d) {
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${y}-${m}-${day}`;
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
        let fetchInFlight = false;

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
            if (fetchInFlight) return;
            const fetchStart = monthStart < loadedStart ? monthStart : loadedStart;
            const fetchEnd = monthEnd > loadedEnd ? monthEnd : loadedEnd;
            // No `types` param: fetch every type for the window and filter
            // client-side in render(). Sending only the currently-active types
            // meant re-enabling a type after navigating never refetched it --
            // `entries` had simply never received it.
            const params = new URLSearchParams({
                start: isoDate(fetchStart),
                end: isoDate(fetchEnd),
            });
            fetchInFlight = true;
            fetch(feedUrl + '?' + params.toString())
                .then((r) => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                })
                .then((data) => {
                    entries = (data.entries || []).map(normalizeEntry);
                    loadedStart = fetchStart;
                    loadedEnd = fetchEnd;
                    render();
                })
                .catch((err) => {
                    console.error('Calendar fetch failed:', err);
                })
                .finally(() => {
                    fetchInFlight = false;
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
                rangeLabel.textContent = anchor.toLocaleDateString(lang, { month: 'long', year: 'numeric' });
            }
        }

        function renderWeekdayHeader() {
            if (!weekdaysEl) return;
            weekdaysEl.innerHTML = '';
            const formatter = new Intl.DateTimeFormat(lang, { weekday: 'short' });
            // Any Monday works -- only the weekday name/order is used.
            const monday = new Date(2026, 0, 5);
            for (let i = 0; i < 7; i++) {
                const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
                const span = document.createElement('span');
                span.className = 'cal-month-weekday';
                span.textContent = formatter.format(d);
                weekdaysEl.appendChild(span);
            }
        }

        // Builds the ordered, capped list of what a day cell shows: events
        // (all-day first, then by time), then birthdays, then presences --
        // presences grouped one chip per place ("Le Chalet · 3") rather than
        // one per person, so a multi-person family stay doesn't flood the cell.
        function buildDayItems(dayEntries, d) {
            const events = dayEntries
                .filter((e) => e.type === 'event')
                .sort((a, b) => {
                    if (a.all_day !== b.all_day) return a.all_day ? -1 : 1;
                    return (a.start || '').localeCompare(b.start || '');
                });
            const birthdays = dayEntries.filter((e) => e.type === 'birthday');
            const presences = dayEntries.filter((e) => e.type === 'presence');

            const items = [];
            events.forEach((e) => {
                const timed = !e.all_day && sameDay(d, e.startDate);
                items.push({
                    type: 'event',
                    url: e.url,
                    time: timed ? (e.start || '').slice(11, 16) : '',
                    label: e.title,
                });
            });
            birthdays.forEach((e) => {
                items.push({ type: 'birthday', url: e.url, time: '', label: e.title });
            });
            const byPlace = new Map();
            presences.forEach((e) => {
                const key = e.subtitle || e.title;
                if (!byPlace.has(key)) byPlace.set(key, { url: e.url, place: e.subtitle || e.title, count: 0 });
                byPlace.get(key).count += 1;
            });
            byPlace.forEach((group) => {
                items.push({
                    type: 'presence',
                    url: group.url,
                    time: '',
                    label: group.count > 1 ? `${group.place} · ${group.count}` : group.place,
                });
            });
            return items;
        }

        function buildEntryLink(item) {
            const link = document.createElement('a');
            link.className = 'cal-month-entry cal-type-' + item.type;
            link.href = item.url || '#';
            if (item.time) {
                const time = document.createElement('span');
                time.className = 'cal-month-entry__time';
                time.textContent = item.time;
                link.appendChild(time);
            }
            const label = document.createElement('span');
            label.className = 'cal-month-entry__label';
            label.textContent = item.label;
            link.appendChild(label);
            return link;
        }

        function renderMonthGrid(monthStart, monthEnd, visible) {
            renderWeekdayHeader();
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
                const weekday = d.getDay();
                if (weekday === 0 || weekday === 6) cell.classList.add('cal-month-cell--weekend');

                const label = document.createElement('span');
                label.className = 'cal-month-cell__day';
                label.textContent = String(day);
                cell.appendChild(label);

                const dayEntries = visible.filter((e) => e.startDate <= d && e.endDate >= d);
                const items = buildDayItems(dayEntries, d);
                if (items.length > 0) {
                    const list = document.createElement('ul');
                    list.className = 'cal-month-cell__entries';
                    items.slice(0, 3).forEach((item) => {
                        const li = document.createElement('li');
                        li.appendChild(buildEntryLink(item));
                        list.appendChild(li);
                    });
                    if (items.length > 3) {
                        const more = document.createElement('li');
                        const moreEl = document.createElement('span');
                        moreEl.className = 'cal-month-more';
                        moreEl.textContent = `+${items.length - 3}`;
                        moreEl.title = items
                            .slice(3)
                            .map((it) => it.label)
                            .join(', ');
                        more.appendChild(moreEl);
                        list.appendChild(more);
                    }
                    cell.appendChild(list);
                }
                monthGrid.appendChild(cell);
            }
            // Filler cells so the final week is complete, same as the leading blanks.
            const totalCells = firstWeekday + daysInMonth;
            const trailing = (7 - (totalCells % 7)) % 7;
            for (let i = 0; i < trailing; i++) {
                const filler = document.createElement('div');
                filler.className = 'cal-month-cell cal-month-cell--empty';
                monthGrid.appendChild(filler);
            }
        }

        function renderAgenda(visible) {
            agenda.innerHTML = '';
            const sorted = visible.slice().sort((a, b) => a.startDate - b.startDate);
            if (sorted.length === 0) {
                const empty = document.createElement('p');
                empty.className = 'fb-meta';
                empty.textContent = gettext('Rien de prévu ce mois-ci.');
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
                date.textContent = e.startDate.toLocaleDateString(lang, { day: 'numeric', month: 'short', year: 'numeric' });
                item.appendChild(date);

                agenda.appendChild(item);
            });
        }

        render();
    }
})();
