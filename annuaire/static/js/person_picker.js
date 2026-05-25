(function () {
    const picker = document.querySelector('.person-picker');
    if (!picker) return;

    const searchUrl = picker.dataset.searchUrl;
    const fieldName = picker.dataset.fieldName || 'persons';
    const singleSelect = picker.dataset.singleSelect === 'true';
    const input = picker.querySelector('.person-picker-input');
    const resultsList = picker.querySelector('.person-picker-results');
    const selectedZone = picker.querySelector('.person-picker-selected');
    const hiddenInputsZone = picker.querySelector('.person-picker-hidden-inputs');

    const selectedIds = new Set();
    let highlightedIndex = -1;
    let debounceTimer = null;

    function getSelectedIdsCsv() {
        return Array.from(selectedIds).join(',');
    }

    function closeDropdown() {
        resultsList.innerHTML = '';
        resultsList.hidden = true;
        highlightedIndex = -1;
    }

    function renderResults(results) {
        resultsList.innerHTML = '';
        if (results.length === 0) {
            const li = document.createElement('li');
            li.className = 'person-picker-empty';
            li.textContent = 'Aucun résultat';
            resultsList.appendChild(li);
            resultsList.hidden = false;
            highlightedIndex = -1;
            return;
        }
        results.forEach((p, idx) => {
            const li = document.createElement('li');
            li.className = 'person-picker-result';
            li.setAttribute('role', 'option');
            li.dataset.id = p.id;
            li.dataset.name = p.name;
            li.textContent = p.name;
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                addPerson(p.id, p.name);
            });
            resultsList.appendChild(li);
        });
        resultsList.hidden = false;
        highlightedIndex = 0;
        updateHighlight();
    }

    function updateHighlight() {
        const items = resultsList.querySelectorAll('.person-picker-result');
        items.forEach((el, idx) => {
            el.classList.toggle('highlighted', idx === highlightedIndex);
        });
    }

    function addPerson(id, name) {
        if (selectedIds.has(String(id))) return;
        if (singleSelect) {
            Array.from(selectedIds).forEach((existingId) => removePerson(existingId));
        }
        selectedIds.add(String(id));

        const badge = document.createElement('span');
        badge.className = 'badge bg-secondary me-1 mb-1 person-picker-badge';
        badge.dataset.id = id;
        badge.textContent = name + ' ';
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white btn-close-sm ms-1';
        closeBtn.setAttribute('aria-label', 'Retirer ' + name);
        closeBtn.addEventListener('click', () => removePerson(id));
        badge.appendChild(closeBtn);
        selectedZone.appendChild(badge);

        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = fieldName;
        hidden.value = id;
        hidden.dataset.id = id;
        hiddenInputsZone.appendChild(hidden);

        input.value = '';
        closeDropdown();
        input.focus();
    }

    function removePerson(id) {
        selectedIds.delete(String(id));
        const badge = selectedZone.querySelector('.person-picker-badge[data-id="' + id + '"]');
        if (badge) badge.remove();
        const hidden = hiddenInputsZone.querySelector('input[data-id="' + id + '"]');
        if (hidden) hidden.remove();
    }

    function search(query) {
        const url = new URL(searchUrl, window.location.origin);
        url.searchParams.set('q', query);
        const csv = getSelectedIdsCsv();
        if (csv) url.searchParams.set('exclude', csv);
        fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.json())
            .then(data => renderResults(data.results || []))
            .catch(() => closeDropdown());
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
                const item = items[highlightedIndex];
                addPerson(item.dataset.id, item.dataset.name);
            }
        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    });

    document.addEventListener('click', (e) => {
        if (!picker.contains(e.target)) closeDropdown();
    });

    function initFromDataset() {
        const raw = picker.dataset.initialSelection;
        if (!raw) return;
        try {
            const items = JSON.parse(raw);
            items.forEach((item) => addPerson(item.id, item.name));
        } catch (e) {
            // Ignore malformed initial selection.
        }
    }

    initFromDataset();
})();
