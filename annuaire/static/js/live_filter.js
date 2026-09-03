// Live list filtering, shared by the annuaire (#110) and the documents list.
//
// Markup contract:
//   form[data-live-filter="<results container selector>"]
//     - every [name] control inside the form is a filter parameter
//     - a control may carry data-live-filter-default="x" to keep x out of the URL
//     - free-text inputs are debounced; every other control applies on change
//   [data-live-filter-reset]      -- "Effacer" link: hidden while no filter is set
//   [data-live-filter-carry="a,b"] -- link whose href must keep filter params a and b
//
// The reset/carry links are looked up document-wide rather than inside the form: both
// sit outside it (page header, toolbar), and there is one filter per page. They exist
// because the swapped-in partial cannot update anything outside itself -- the annuaire's
// "Effacer" link never appeared when you typed, and stayed behind after you cleared the
// box, because it lives in the page header.
(function () {
    const DEBOUNCE_MS = 200;

    document.querySelectorAll('form[data-live-filter]').forEach(initLiveFilter);

    function initLiveFilter(form) {
        const results = document.querySelector(form.dataset.liveFilter);
        if (!results) return;

        const controls = Array.from(form.querySelectorAll('[name]'));
        const resetLink = document.querySelector('[data-live-filter-reset]');
        const carryLinks = Array.from(document.querySelectorAll('[data-live-filter-carry]'));
        let debounceTimer = null;
        let requestSeq = 0;

        function currentParams() {
            const params = new URLSearchParams();
            controls.forEach((control) => {
                const value = control.value.trim();
                if (!value || value === (control.dataset.liveFilterDefault || '')) return;
                params.set(control.name, value);
            });
            return params;
        }

        function buildUrl(params) {
            const url = new URL(form.getAttribute('action') || window.location.pathname, window.location.origin);
            url.search = params.toString();
            return url;
        }

        function syncLinks(params) {
            if (resetLink) resetLink.hidden = params.toString() === '';
            carryLinks.forEach((link) => {
                const path = new URL(link.getAttribute('href'), window.location.origin).pathname;
                const carried = new URLSearchParams();
                link.dataset.liveFilterCarry
                    .split(',')
                    .map((name) => name.trim())
                    .filter(Boolean)
                    .forEach((name) => {
                        const value = params.get(name);
                        if (value) carried.set(name, value);
                    });
                const query = carried.toString();
                link.setAttribute('href', query ? `${path}?${query}` : path);
            });
        }

        function refresh() {
            const params = currentParams();
            const url = buildUrl(params);
            const seq = (requestSeq += 1);
            results.setAttribute('aria-busy', 'true');
            results.classList.add('opacity-50');
            fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then((response) => {
                    if (seq !== requestSeq) return null; // a newer request has since started
                    if (!response.ok) throw new Error('live filter request failed');
                    return response.text();
                })
                .then((html) => {
                    if (html === null || seq !== requestSeq) return;
                    results.innerHTML = html;
                    syncLinks(params);
                    window.history.replaceState(null, '', url.pathname + url.search);
                })
                .catch(() => {
                    // Fail quiet: leave whatever results are currently shown in place.
                })
                .finally(() => {
                    if (seq !== requestSeq) return;
                    results.removeAttribute('aria-busy');
                    results.classList.remove('opacity-50');
                });
        }

        controls.forEach((control) => {
            const isFreeText = control.tagName === 'INPUT' && ['text', 'search'].includes(control.type);
            if (isFreeText) {
                control.addEventListener('input', () => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(refresh, DEBOUNCE_MS);
                });
            } else {
                control.addEventListener('change', () => {
                    clearTimeout(debounceTimer);
                    refresh();
                });
            }
        });

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            clearTimeout(debounceTimer);
            refresh();
        });
    }
})();
