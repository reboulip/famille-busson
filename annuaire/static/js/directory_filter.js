(function () {
    const form = document.getElementById('directory-filter-form');
    const resultsContainer = document.getElementById('directory-results');
    if (!form || !resultsContainer) return;

    const searchInput = document.getElementById('directory-search');
    const sortSelect = form.querySelector('select[name="sort"]');
    if (!searchInput || !sortSelect) return;

    const DEBOUNCE_MS = 200;
    const DEFAULT_SORT = 'recent';

    let debounceTimer = null;
    let requestSeq = 0;

    function buildUrl() {
        const url = new URL(form.action, window.location.origin);
        const q = searchInput.value.trim();
        const sort = sortSelect.value;
        if (q) url.searchParams.set('q', q);
        if (sort && sort !== DEFAULT_SORT) url.searchParams.set('sort', sort);
        return url;
    }

    function refresh() {
        const url = buildUrl();
        const seq = (requestSeq += 1);
        resultsContainer.setAttribute('aria-busy', 'true');
        resultsContainer.classList.add('opacity-50');
        fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then((response) => {
                if (seq !== requestSeq) return null; // a newer request has since started
                if (!response.ok) throw new Error('directory filter request failed');
                return response.text();
            })
            .then((html) => {
                if (html === null || seq !== requestSeq) return;
                resultsContainer.innerHTML = html;
                window.history.replaceState(null, '', url.pathname + url.search);
            })
            .catch(() => {
                // Fail quiet: leave whatever results are currently shown in place.
            })
            .finally(() => {
                if (seq !== requestSeq) return;
                resultsContainer.removeAttribute('aria-busy');
                resultsContainer.classList.remove('opacity-50');
            });
    }

    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(refresh, DEBOUNCE_MS);
    });

    sortSelect.addEventListener('change', () => {
        clearTimeout(debounceTimer);
        refresh();
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        clearTimeout(debounceTimer);
        refresh();
    });
})();
