(function () {
    const { parseISODate, midnight, addDays, addMonths, dayDiff, sameDay, formatDayHeader, formatDate, initNavigation } =
        window.FBCalendar;

    const calendars = document.querySelectorAll('.presence-calendar');
    calendars.forEach(initCalendar);

    function initCalendar(root) {
        const grid = root.querySelector('.presence-calendar-grid');
        const rangeLabel = root.querySelector('.presence-calendar-range');
        if (!grid) return;

        let presences;
        try {
            presences = JSON.parse(root.dataset.presences || '[]');
        } catch (e) {
            presences = [];
        }
        presences = presences.map((p) => ({
            person: p.person,
            chalet: p.chalet || '',
            start: parseISODate(p.start),
            end: parseISODate(p.end),
        })).filter((p) => p.start && p.end);

        let anchor = midnight(new Date());
        let windowMode = root.dataset.window === 'long' ? 'long' : 'short';

        function setWindow(mode) {
            windowMode = mode;
            render();
        }

        initNavigation(root, {
            onPrev: () => {
                anchor = addMonths(anchor, -1);
                render();
            },
            onNext: () => {
                anchor = addMonths(anchor, 1);
                render();
            },
            onToday: () => {
                anchor = midnight(new Date());
                render();
            },
            onWindowChange: setWindow,
        });

        function computeWindow() {
            if (windowMode === 'long') {
                return [addMonths(anchor, -1), addMonths(anchor, 5)];
            }
            return [addDays(anchor, -7), addDays(anchor, 35)];
        }

        function render() {
            const [winStart, winEnd] = computeWindow();
            const today = midnight(new Date());

            const days = [];
            for (let d = new Date(winStart); d <= winEnd; d = addDays(d, 1)) {
                days.push(new Date(d));
            }
            const nCols = days.length;

            const visible = presences.filter((p) => p.end >= winStart && p.start <= winEnd);
            const persons = Array.from(new Set(visible.map((p) => p.person))).sort();

            grid.style.setProperty('--cal-cols', String(nCols));
            grid.innerHTML = '';

            // Header row
            const corner = document.createElement('div');
            corner.className = 'cal-corner';
            corner.style.gridRow = '1';
            corner.style.gridColumn = '1';
            grid.appendChild(corner);

            days.forEach((d, idx) => {
                const cell = document.createElement('div');
                cell.className = 'cal-day';
                if (sameDay(d, today)) cell.classList.add('cal-day-today');
                if (d.getDay() === 0 || d.getDay() === 6) cell.classList.add('cal-day-weekend');
                if (d.getDate() === 1) cell.classList.add('cal-day-month-start');
                cell.style.gridRow = '1';
                cell.style.gridColumn = String(idx + 2);
                cell.textContent = formatDayHeader(d, windowMode);
                grid.appendChild(cell);
            });

            // Person rows
            persons.forEach((person, rowIdx) => {
                const row = rowIdx + 2;
                const nameCell = document.createElement('div');
                nameCell.className = 'cal-name';
                nameCell.style.gridRow = String(row);
                nameCell.style.gridColumn = '1';
                nameCell.textContent = person;
                grid.appendChild(nameCell);

                const lane = document.createElement('div');
                lane.className = 'cal-lane';
                lane.style.gridRow = String(row);
                lane.style.gridColumn = '2 / span ' + nCols;
                grid.appendChild(lane);

                visible.filter((p) => p.person === person).forEach((p) => {
                    const clampedStart = p.start < winStart ? winStart : p.start;
                    const clampedEnd = p.end > winEnd ? winEnd : p.end;
                    const startCol = dayDiff(winStart, clampedStart) + 2;
                    const endCol = dayDiff(winStart, clampedEnd) + 3;
                    const bar = document.createElement('div');
                    bar.className = 'cal-bar';
                    if (p.end < today) bar.classList.add('bar-past');
                    else if (p.start > today) bar.classList.add('bar-future');
                    else bar.classList.add('bar-current');
                    bar.style.gridRow = String(row);
                    bar.style.gridColumn = startCol + ' / ' + endCol;
                    bar.title = `${p.person}${p.chalet ? ' · ' + p.chalet : ''} (${formatDate(p.start)} → ${formatDate(p.end)})`;
                    bar.textContent = p.chalet;
                    grid.appendChild(bar);
                });
            });

            if (persons.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'cal-empty-message';
                empty.style.gridRow = '2';
                empty.style.gridColumn = '1 / span ' + (nCols + 1);
                empty.textContent = 'Aucune présence dans cette fenêtre.';
                grid.appendChild(empty);
            }

            if (rangeLabel) {
                rangeLabel.textContent = `${formatDate(winStart)} → ${formatDate(winEnd)}`;
            }
        }

        root.querySelectorAll('.cal-window-toggle').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.target === windowMode);
        });
        setWindow(windowMode);
    }
})();
