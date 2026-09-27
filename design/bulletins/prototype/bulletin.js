// Bulletin carousels: progressive enhancement over a CSS scroll-snap track.
//
// Without this script a carousel still works: the track scrolls sideways (swipe, trackpad,
// scrollbar, arrow keys once focused) and "#page-N" links scroll it to that slide. The
// script only adds the previous/next buttons and the "2 / 5" counter, which are hidden
// in the markup until it runs.
(function () {
    'use strict';

    function setUp(root) {
        var track = root.querySelector('[data-carousel-track]');
        var nav = root.querySelector('[data-carousel-nav]');
        if (!track || !nav) return;
        var slides = Array.prototype.slice.call(track.children);
        if (slides.length < 2) return;
        var prev = nav.querySelector('[data-carousel-prev]');
        var next = nav.querySelector('[data-carousel-next]');
        var count = nav.querySelector('[data-carousel-count]');

        // The slide whose left edge is closest to the track's visible left edge. The track is
        // position: relative (see bulletin.css), so slide.offsetLeft is measured from it.
        function currentIndex() {
            var left = track.scrollLeft;
            var best = 0;
            var bestDistance = Infinity;
            slides.forEach(function (slide, i) {
                var distance = Math.abs(slide.offsetLeft - left);
                if (distance < bestDistance) {
                    best = i;
                    bestDistance = distance;
                }
            });
            return best;
        }

        function update() {
            var i = currentIndex();
            var atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
            count.textContent = (i + 1) + ' / ' + slides.length;
            prev.disabled = i === 0;
            next.disabled = atEnd;
        }

        function go(step) {
            var target = slides[Math.min(slides.length - 1, Math.max(0, currentIndex() + step))];
            track.scrollTo({ left: target.offsetLeft, behavior: 'smooth' });
        }

        prev.addEventListener('click', function () { go(-1); });
        next.addEventListener('click', function () { go(1); });
        track.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowLeft') { event.preventDefault(); go(-1); }
            if (event.key === 'ArrowRight') { event.preventDefault(); go(1); }
        });
        var pending = false;
        track.addEventListener('scroll', function () {
            if (pending) return;
            pending = true;
            window.requestAnimationFrame(function () { pending = false; update(); });
        });
        window.addEventListener('resize', update);

        // "p. 6" links target a slide (#page-6): bring it to the front of the strip, not
        // just somewhere into view.
        function showTarget() {
            var target = location.hash ? document.getElementById(decodeURIComponent(location.hash.slice(1))) : null;
            if (target && target.parentElement === track) {
                track.scrollTo({ left: target.offsetLeft, behavior: 'auto' });
            }
        }
        window.addEventListener('hashchange', showTarget);
        showTarget();

        nav.hidden = false;
        update();
    }

    document.querySelectorAll('[data-carousel]').forEach(setUp);
})();
