document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.address-picker-input').forEach(initAddressPicker);
});

function initAddressPicker(input) {
    const searchUrl = input.dataset.searchUrl || 'https://api-adresse.data.gouv.fr/search/';
    const limit = input.dataset.addressLimit || '5';

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

    function composeAddress(properties) {
        const name = properties.name;
        const postcode = properties.postcode;
        const city = properties.city;
        if (name && postcode && city) return name + ', ' + postcode + ' ' + city;
        return properties.label;
    }

    function renderResults(features) {
        resultsList.innerHTML = '';
        if (features.length === 0) {
            const li = document.createElement('li');
            li.className = 'address-picker-empty';
            li.textContent = 'Aucun résultat';
            resultsList.appendChild(li);
            resultsList.hidden = false;
            highlightedIndex = -1;
            return;
        }
        features.forEach((feature) => {
            const props = feature.properties;
            const li = document.createElement('li');
            li.className = 'address-picker-result';
            li.setAttribute('role', 'option');
            const label = document.createElement('div');
            label.textContent = props.label;
            li.appendChild(label);
            if (props.context) {
                const context = document.createElement('small');
                context.className = 'address-picker-context';
                context.textContent = props.context;
                li.appendChild(context);
            }
            li.dataset.address = composeAddress(props);
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                selectAddress(li.dataset.address);
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

    function selectAddress(address) {
        input.value = address;
        closeDropdown();
    }

    function search(query) {
        const url = new URL(searchUrl, window.location.origin);
        url.searchParams.set('q', query);
        url.searchParams.set('limit', limit);
        url.searchParams.set('autocomplete', '1');
        fetch(url.toString())
            .then((r) => r.json())
            .then((data) => renderResults(data.features || []))
            .catch(() => closeDropdown());
    }

    input.addEventListener('input', () => {
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
                selectAddress(items[highlightedIndex].dataset.address);
            }
        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    });

    document.addEventListener('click', (e) => {
        if (!wrapper.contains(e.target)) closeDropdown();
    });
}
