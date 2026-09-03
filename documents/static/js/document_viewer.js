// Zoom steps offered by the PDF toolbar. "Fit" (1) is the default: one CSS pixel of
// page per CSS pixel of container. Everything above it exists because a scanned
// document carries no text layer -- the only way to read small handwriting is more
// pixels (#109).
const PDF_ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];
const PDF_DEFAULT_ZOOM_INDEX = PDF_ZOOM_STEPS.indexOf(1);

// Backing-store ceilings, per page. A canvas costs width*height*4 bytes of (non-JS-heap)
// memory the moment it is rendered, so 3x zoom on a wide container would otherwise ask
// for hundreds of MB for a single page and simply fail on mobile. Past these limits the
// page still grows on screen, it just stops gaining real resolution.
// (Same ceilings, and the same reasoning, as family_tree.js's image export: iOS Safari
// silently fails past ~16.7M pixels, and 8192 is half html-to-image's canvas dimension
// limit.) 16M pixels is ~64MB per live page -- affordable because the retain margin
// below keeps only the few pages around the viewport rendered at any moment.
const PDF_MAX_CANVAS_SIDE = 8192;
const PDF_MAX_CANVAS_AREA = 16e6;

// Render a page once it is within this much of the viewport...
const PDF_RENDER_MARGIN = '400px 0px';
// ...and hand its pixels back once it is further away than this. Without the second
// margin a long scan keeps every page it has ever shown: 60 A4 pages at fit width is
// ~117M pixels, ~450MB that is never reclaimed (#109).
const PDF_RETAIN_MARGIN = '2000px 0px';

document.addEventListener('DOMContentLoaded', () => {
    // Full-screen: CSS fixed overlay, matching the genealogy tree's documented pattern
    // (main.css's .genealogie-panel--fullscreen) -- no permission/gesture dance, and it
    // keeps the toolbar (caption, download, exit) visible and usable.
    document.querySelectorAll('.document-viewer').forEach((viewer) => {
        const fullscreenBtn = viewer.querySelector('.document-viewer-fullscreen-btn');
        const strip = viewer.querySelector('.document-viewer-strip');
        const carousel = strip ? initImageCarousel(viewer, strip) : null;
        const pdf = viewer.querySelector('.document-viewer-pdf-pages') ? initPdfViewer(viewer) : null;

        const setFullscreen = (active) => {
            viewer.classList.toggle('document-viewer--fullscreen', active);
            if (fullscreenBtn) fullscreenBtn.textContent = active ? '✕ Quitter le plein écran' : '⛶ Plein écran';
            // The stage just changed width; PDF pages are sized in real pixels, so they
            // have to be re-measured and re-rendered or fullscreen shows the same small
            // page inside a bigger box (#109).
            if (pdf) pdf.relayout();
        };
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                setFullscreen(!viewer.classList.contains('document-viewer--fullscreen'));
            });
        }
        document.addEventListener('keydown', (e) => {
            if (!viewer.classList.contains('document-viewer--fullscreen')) return;
            if (e.key === 'Escape') {
                setFullscreen(false);
            } else if (carousel && e.key === 'ArrowLeft') {
                carousel.navigate(-1);
            } else if (carousel && e.key === 'ArrowRight') {
                carousel.navigate(1);
            }
        });

        // Zoom: click-to-toggle between "fit" (shrunk to its container) and "1:1"
        // (natural size, scrollable within .document-viewer-stage's own overflow:
        // auto). Native pinch-zoom is left to the browser (touch-action: pinch-zoom
        // in CSS) rather than a custom gesture handler. Exception: clicking an image
        // in the non-fullscreen multi-image strip enters fullscreen positioned on
        // that image instead of zooming in place -- zooming there would fight the
        // strip's own horizontal scroll-snap (#111).
        viewer.querySelectorAll('.document-viewer-zoomable').forEach((img) => {
            img.addEventListener('click', () => {
                const isStripImage = carousel && strip.contains(img);
                const isFullscreen = viewer.classList.contains('document-viewer--fullscreen');
                if (isStripImage && !isFullscreen) {
                    setFullscreen(true);
                    // Jump instantly (no smooth scroll) -- the strip's width just
                    // changed with the fullscreen layout, so an animated scroll
                    // would race that resize and can land on the wrong offset.
                    carousel.goTo(carousel.indexOf(img), { smooth: false });
                    return;
                }
                img.classList.toggle('document-viewer-zoomable--zoomed');
            });
        });
    });
});

function initImageCarousel(viewer, strip) {
    const items = Array.from(strip.querySelectorAll('.document-viewer-strip-item'));
    const images = items.map((item) => item.querySelector('img'));
    const counter = viewer.querySelector('.document-viewer-carousel-counter');
    const prevBtn = viewer.querySelector('.document-viewer-carousel-prev');
    const nextBtn = viewer.querySelector('.document-viewer-carousel-next');
    let currentIndex = 0;

    function updateCounter() {
        if (counter) counter.textContent = `${currentIndex + 1} / ${items.length}`;
    }

    function goTo(index, options) {
        currentIndex = ((index % items.length) + items.length) % items.length;
        strip.scrollTo({ left: items[currentIndex].offsetLeft, behavior: (options && options.smooth) === false ? 'auto' : 'smooth' });
        updateCounter();
    }

    function navigate(delta) {
        goTo(currentIndex + delta);
    }

    function indexOf(img) {
        return images.indexOf(img);
    }

    // The strip is a native scroll-snap container, so a swipe (the primary gesture on
    // mobile, where fullscreen locks to one image per screen) moves it without going
    // through goTo(). Track the scroll position too, or the counter keeps reading
    // "1 / 4" after a swipe and the next/prev buttons then step from the stale index
    // -- pressing "next" after swiping to image 3 used to jump backwards to 2 (#111).
    let scrollFrame = null;
    strip.addEventListener('scroll', () => {
        if (scrollFrame) return;
        scrollFrame = requestAnimationFrame(() => {
            scrollFrame = null;
            const stripCentre = strip.scrollLeft + strip.clientWidth / 2;
            let closest = 0;
            let closestDistance = Infinity;
            items.forEach((item, index) => {
                const distance = Math.abs(item.offsetLeft + item.offsetWidth / 2 - stripCentre);
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closest = index;
                }
            });
            if (closest !== currentIndex) {
                currentIndex = closest;
                updateCounter();
            }
        });
    });

    if (prevBtn) prevBtn.addEventListener('click', () => navigate(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigate(1));

    return { navigate, goTo, indexOf };
}

// PDF rendering via pdf.js -- <embed> renders nothing at all on many mobile
// browsers (no PDF plugin), so every PDF goes through canvas instead, on every
// device.
function initPdfViewer(viewer) {
    const container = viewer.querySelector('.document-viewer-pdf-pages');
    const stage = container.closest('.document-viewer-stage');
    const zoomInBtn = viewer.querySelector('.document-viewer-zoom-in');
    const zoomOutBtn = viewer.querySelector('.document-viewer-zoom-out');
    const zoomLabel = viewer.querySelector('.document-viewer-zoom-level');

    let pdfDoc = null;
    let pages = [];
    let zoomIndex = PDF_DEFAULT_ZOOM_INDEX;
    let renderObserver = null;
    let retainObserver = null;
    let layoutToken = 0;
    let lastFitWidth = 0;

    // Canvas pixels per CSS pixel. Rendering at 1:1 was what made scanned pages
    // unreadable on any HiDPI screen: a phone at devicePixelRatio 3 was showing an
    // A4 page through 324 physical-pixel-wide artwork (#109).
    function backingScale() {
        return window.devicePixelRatio || 1;
    }

    // Keep the requested scale inside the per-page ceilings above, preserving the
    // aspect ratio (both dimensions shrink by the same factor).
    function clampScale(scale, baseViewport) {
        const width = baseViewport.width * scale;
        const height = baseViewport.height * scale;
        const limit = Math.min(
            PDF_MAX_CANVAS_SIDE / width,
            PDF_MAX_CANVAS_SIDE / height,
            Math.sqrt(PDF_MAX_CANVAS_AREA / (width * height)),
            1,
        );
        return scale * limit;
    }

    function updateZoomControls() {
        if (zoomLabel) zoomLabel.textContent = `${Math.round(PDF_ZOOM_STEPS[zoomIndex] * 100)} %`;
        if (zoomOutBtn) zoomOutBtn.disabled = zoomIndex === 0;
        if (zoomInBtn) zoomInBtn.disabled = zoomIndex === PDF_ZOOM_STEPS.length - 1;
    }

    async function renderPage(entry) {
        if (entry.rendered) return;
        entry.rendered = true;
        entry.canvas.width = Math.max(1, Math.floor(entry.viewport.width));
        entry.canvas.height = Math.max(1, Math.floor(entry.viewport.height));
        try {
            entry.task = entry.page.render({ canvasContext: entry.canvas.getContext('2d'), viewport: entry.viewport });
            await entry.task.promise;
        } catch {
            // Cancelled by a relayout, or a genuine render failure -- either way the
            // page stays eligible for a later attempt.
            entry.rendered = false;
        } finally {
            entry.task = null;
        }
    }

    // Give the pixels back. The canvas keeps its CSS width/height, so collapsing the
    // backing store to 1x1 frees the memory without moving anything on the page --
    // scrolling back re-renders it.
    function releasePage(entry) {
        if (!entry.rendered) return;
        if (entry.task) entry.task.cancel();
        entry.rendered = false;
        entry.canvas.width = 1;
        entry.canvas.height = 1;
    }

    function disconnectObservers() {
        if (renderObserver) renderObserver.disconnect();
        if (retainObserver) retainObserver.disconnect();
        renderObserver = null;
        retainObserver = null;
    }

    function findEntry(canvas) {
        return pages.find((entry) => entry.canvas === canvas);
    }

    // Two passes, as before (#109): size every canvas up front so the container
    // reaches its final height before anything renders -- rendering incrementally let
    // the browser's scroll anchoring drag scrollTop away from 0 as each page was
    // appended. Now also re-run on zoom, fullscreen and resize, since the canvas
    // carries real pixels rather than a CSS-stretched bitmap.
    async function layout(preserveScroll) {
        if (!pdfDoc) return;
        const token = (layoutToken += 1);
        const previousRatio = preserveScroll && stage.scrollHeight ? stage.scrollTop / stage.scrollHeight : 0;

        disconnectObservers();
        pages.forEach((entry) => {
            if (entry.task) entry.task.cancel();
        });

        const fitWidth = container.clientWidth || 600;
        lastFitWidth = fitWidth;
        const cssWidth = fitWidth * PDF_ZOOM_STEPS[zoomIndex];
        const dpr = backingScale();
        const built = [];
        const fragment = document.createDocumentFragment();

        for (let pageNumber = 1; pageNumber <= pdfDoc.numPages; pageNumber += 1) {
            const page = await pdfDoc.getPage(pageNumber);
            if (token !== layoutToken) return;
            const baseViewport = page.getViewport({ scale: 1 });
            const cssScale = cssWidth / baseViewport.width;
            const viewport = page.getViewport({ scale: Math.max(clampScale(cssScale * dpr, baseViewport), 0.01) });
            const canvas = document.createElement('canvas');
            canvas.className = 'document-viewer-pdf-page';
            // Start collapsed rather than at the 300x150 default: 60 not-yet-rendered
            // pages would otherwise reserve ~11MB between them before a single one is
            // drawn. renderPage() sizes the store when the page comes into view.
            canvas.width = 1;
            canvas.height = 1;
            // Explicit CSS box: independent of the backing store, so a released page
            // holds its place and a clamped one still fills the requested width.
            canvas.style.width = `${Math.round(cssWidth)}px`;
            canvas.style.height = `${Math.round(baseViewport.height * cssScale)}px`;
            fragment.appendChild(canvas);
            built.push({ canvas, page, viewport, rendered: false, task: null });
        }

        if (token !== layoutToken) return;
        container.replaceChildren(fragment);
        pages = built;
        stage.scrollTop = previousRatio ? previousRatio * stage.scrollHeight : 0;

        renderObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;
                    const target = findEntry(entry.target);
                    if (target) renderPage(target);
                });
            },
            { root: stage, rootMargin: PDF_RENDER_MARGIN },
        );
        retainObserver = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) return;
                    const target = findEntry(entry.target);
                    if (target) releasePage(target);
                });
            },
            { root: stage, rootMargin: PDF_RETAIN_MARGIN },
        );
        pages.forEach(({ canvas }) => {
            renderObserver.observe(canvas);
            retainObserver.observe(canvas);
        });
    }

    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', () => {
            if (zoomIndex >= PDF_ZOOM_STEPS.length - 1) return;
            zoomIndex += 1;
            updateZoomControls();
            layout(true);
        });
    }
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', () => {
            if (zoomIndex <= 0) return;
            zoomIndex -= 1;
            updateZoomControls();
            layout(true);
        });
    }

    // Only a real width change matters -- a vertical scrollbar appearing, or a phone's
    // address bar collapsing, fires resize without changing what we measured.
    let resizeTimer = null;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if ((container.clientWidth || 600) !== lastFitWidth) layout(true);
        }, 200);
    });

    updateZoomControls();

    (async () => {
        const { pdfUrl, pdfjsSrc, pdfjsWorkerSrc } = container.dataset;
        try {
            const pdfjsLib = await import(pdfjsSrc);
            pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerSrc;
            // pdf.js 6.x requires an options object -- a bare URL string is silently
            // read as {} and fails with "expected either `data`, `range`, or `url`".
            pdfDoc = await pdfjsLib.getDocument({ url: pdfUrl }).promise;
            container.replaceChildren();
            await layout(false);
        } catch (error) {
            console.error('Échec du rendu PDF :', error);
            container.textContent = "Impossible d'afficher ce PDF ici. ";
            const link = document.createElement('a');
            link.href = `${pdfUrl}?download=1`;
            link.textContent = 'Télécharger le fichier';
            container.appendChild(link);
        }
    })();

    return { relayout: () => layout(true) };
}
