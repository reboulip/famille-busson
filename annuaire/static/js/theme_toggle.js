/* Alpenglow / Nightfall toggle.
 *
 * The *initial* theme is applied by a tiny inline script in base.html's <head>
 * -- it has to run before the stylesheets paint or the page flashes the wrong
 * palette. This file only handles the toggle button and keeping its label in
 * sync; it can safely load at the end of <body>.
 *
 * Three states, matching tokens.css:
 *   data-bs-theme="light"  explicit Alpenglow
 *   data-bs-theme="dark"   explicit Nightfall
 *   (no attribute)         follow the OS via prefers-color-scheme
 *
 * The button toggles between the two explicit states rather than cycling
 * through "system": a three-way toggle with no visible indicator of which of
 * the three you are in is worse than a two-way one, and the OS preference is
 * still what decides on a first visit.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'fb-theme';
    const root = document.documentElement;

    function currentTheme() {
        const explicit = root.getAttribute('data-bs-theme');
        if (explicit === 'dark' || explicit === 'light') {
            return explicit;
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    /* The button always offers the theme you are *not* in. */
    function syncButtons(theme) {
        const goingTo = theme === 'dark' ? 'Alpenglow' : 'Nightfall';
        document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
            const label = btn.querySelector('[data-theme-label]');
            const icon = btn.querySelector('[data-theme-icon] svg');
            if (label) {
                label.textContent = goingTo;
            }
            if (icon) {
                /* The sun and moon glyphs live in the same 24x24 grid, so
                   swapping only the path data keeps the box identical. */
                icon.innerHTML = theme === 'dark' ? SUN_PATHS : MOON_PATHS;
            }
            btn.setAttribute('title', 'Passer au thème ' + goingTo);
        });
    }

    const MOON_PATHS = '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>';
    const SUN_PATHS =
        '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2"/><path d="M12 19.5v2"/>' +
        '<path d="M2.5 12h2"/><path d="M19.5 12h2"/><path d="m5.2 5.2 1.4 1.4"/>' +
        '<path d="m17.4 17.4 1.4 1.4"/><path d="m18.8 5.2-1.4 1.4"/><path d="m6.6 17.4-1.4 1.4"/>';

    document.addEventListener('click', function (event) {
        const btn = event.target.closest('[data-theme-toggle]');
        if (!btn) {
            return;
        }
        const next = currentTheme() === 'dark' ? 'light' : 'dark';
        root.setAttribute('data-bs-theme', next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (e) {
            /* Private mode or storage blocked -- the choice just won't persist
               past this page load, which is a better outcome than throwing. */
        }
        syncButtons(next);
    });

    syncButtons(currentTheme());
})();
