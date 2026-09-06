(function () {
    'use strict';

    // Mobile profile view (#124): the identity card sticks below the top bar and
    // condenses to name + photo once the page has scrolled past it, so the rest of
    // the profile is not read through a full-height info card.
    //
    // Markup contract (personne_detail.html): .profile-identity is the identity
    // card, immediately preceded by a zero-height .profile-identity-sentinel. All
    // the condensing itself is CSS, gated on the mobile breakpoint -- this script
    // only reports whether the sentinel is still on screen.

    const identity = document.querySelector('.profile-identity');
    const sentinel = document.querySelector('.profile-identity-sentinel');
    if (!identity || !sentinel) return;

    // The top bar's height comes from several rules at once, so it is measured
    // and published rather than duplicated as a magic number in the stylesheet
    // (same approach as family_tree.js's label width). The observer below reuses
    // the same measurement for its rootMargin, so the sentinel is judged "gone"
    // right where the identity card starts sticking, not some pixels late.
    const topbar = document.querySelector('.fb-topbar');

    // An observer rather than a scroll listener: it fires only at the crossing,
    // so nothing runs per frame while the page is moving. rootMargin is fixed at
    // construction time, so a topbar height change means recreating it rather
    // than mutating an existing instance.
    let observer = null;
    const createObserver = function (topbarHeight) {
        if (observer) observer.disconnect();
        observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    identity.classList.toggle('profile-identity--pinned', !entry.isIntersecting);
                });
            },
            { threshold: 0, rootMargin: topbarHeight ? '-' + topbarHeight + 'px 0px 0px 0px' : '0px' }
        );
        observer.observe(sentinel);
    };

    if (topbar) {
        const publishOffset = function () {
            const height = Math.round(topbar.getBoundingClientRect().height);
            document.documentElement.style.setProperty('--profile-sticky-top', height + 'px');
            createObserver(height);
        };
        publishOffset();
        window.addEventListener('resize', publishOffset);
    } else {
        // No top bar found (shouldn't happen in practice) -- still observe, just
        // without an offset.
        createObserver(0);
    }
})();
