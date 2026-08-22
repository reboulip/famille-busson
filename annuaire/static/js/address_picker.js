document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.address-picker-input').forEach(initAddressPicker);
});

function initAddressPicker(input) {
    const searchUrl = input.dataset.searchUrl;
    const limit = input.dataset.addressLimit || '5';
    const latTarget = input.dataset.latTarget ? document.getElementById(input.dataset.latTarget) : null;
    const lonTarget = input.dataset.lonTarget ? document.getElementById(input.dataset.lonTarget) : null;

    const wrapper = document.createElement('div');
    wrapper.className = 'address-picker';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const resultsList = document.createElement('ul');
    resultsList.className = 'address-picker-results';
    resultsList.setAttribute('role', 'listbox');
    resultsList.hidden = true;
    wrapper.appendChild(resultsList);

    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');

    let highlightedIndex = -1;
    let debounceTimer = null;

    function closeDropdown() {
        resultsList.innerHTML = '';
        resultsList.hidden = true;
        highlightedIndex = -1;
        input.setAttribute('aria-expanded', 'false');
    }

    function renderResults(results) {
        resultsList.innerHTML = '';
        if (results.length === 0) {
            const li = document.createElement('li');
            li.className = 'address-picker-empty';
            li.textContent = 'Aucun résultat';
            resultsList.appendChild(li);
            resultsList.hidden = false;
            highlightedIndex = -1;
            return;
        }
        results.forEach((result) => {
            const li = document.createElement('li');
            li.className = 'address-picker-result';
            li.setAttribute('role', 'option');
            const label = document.createElement('div');
            label.textContent = result.label;
            li.appendChild(label);
            if (result.context) {
                const context = document.createElement('small');
                context.className = 'address-picker-context';
                context.textContent = result.context;
                li.appendChild(context);
            }
            li.dataset.address = result.address;
            li.dataset.lat = result.lat;
            li.dataset.lon = result.lon;
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                selectAddress(li);
            });
            resultsList.appendChild(li);
        });
        resultsList.hidden = false;
        highlightedIndex = 0;
        input.setAttribute('aria-expanded', 'true');
        updateHighlight();
    }

    function updateHighlight() {
        const items = resultsList.querySelectorAll('.address-picker-result');
        items.forEach((el, idx) => {
            el.classList.toggle('highlighted', idx === highlightedIndex);
        });
    }

    function selectAddress(li) {
        input.value = li.dataset.address;
        if (latTarget && lonTarget) {
            latTarget.value = li.dataset.lat || '';
            lonTarget.value = li.dataset.lon || '';
        }
        closeDropdown();
    }

    function search(query) {
        const url = new URL(searchUrl, window.location.origin);
        url.searchParams.set('q', query);
        url.searchParams.set('limit', limit);
        fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then((r) => r.json())
            .then((data) => renderResults(data.results || []))
            .catch(() => closeDropdown());
    }

    input.addEventListener('input', () => {
        // Typing invalidates any coordinates captured from a previous selection --
        // otherwise the map could show a stale pin for text that no longer matches it.
        if (latTarget) latTarget.value = '';
        if (lonTarget) lonTarget.value = '';
        clearTimeout(debounceTimer);
        const q = input.value.trim();
        if (q.length < 3) {
            closeDropdown();
            return;
        }
        debounceTimer = setTimeout(() => search(q), 300);
    });

    input.addEventListener('keydown', (e) => {
        const items = resultsList.querySelectorAll('.address-picker-result');
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
                selectAddress(items[highlightedIndex]);
            }
        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    });

    document.addEventListener('click', (e) => {
        if (!wrapper.contains(e.target)) closeDropdown();
    });
}
