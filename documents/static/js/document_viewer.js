document.addEventListener('DOMContentLoaded', () => {
    // Full-screen: CSS fixed overlay, matching the genealogy tree's documented pattern
    // (main.css's .genealogie-panel--fullscreen) -- no permission/gesture dance, and it
    // keeps the toolbar (caption, download, exit) visible and usable.
    document.querySelectorAll('.document-viewer').forEach((viewer) => {
        const fullscreenBtn = viewer.querySelector('.document-viewer-fullscreen-btn');
        if (!fullscreenBtn) return;
        const setFullscreen = (active) => {
            viewer.classList.toggle('document-viewer--fullscreen', active);
            fullscreenBtn.textContent = active ? '✕ Quitter le plein écran' : '⛶ Plein écran';
        };
        fullscreenBtn.addEventListener('click', () => {
            setFullscreen(!viewer.classList.contains('document-viewer--fullscreen'));
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && viewer.classList.contains('document-viewer--fullscreen')) {
                setFullscreen(false);
            }
        });
    });

    // PDF rendering via pdf.js -- <embed> renders nothing at all on many mobile
    // browsers (no PDF plugin), so every PDF goes through canvas instead, on every
    // device.
    document.querySelectorAll('.document-viewer-pdf-pages').forEach((container) => {
        renderPdf(container);
    });

    // Zoom: click-to-toggle between "fit" (shrunk to its container) and "1:1"
    // (natural size, scrollable within .document-viewer-stage's own overflow: auto).
    // Native pinch-zoom is left to the browser (touch-action: pinch-zoom in CSS)
    // rather than a custom gesture handler.
    document.querySelectorAll('.document-viewer-zoomable').forEach((img) => {
        img.addEventListener('click', () => {
            img.classList.toggle('document-viewer-zoomable--zoomed');
        });
    });
});

async function renderPdf(container) {
    const { pdfUrl, pdfjsSrc, pdfjsWorkerSrc } = container.dataset;
    try {
        const pdfjsLib = await import(pdfjsSrc);
        pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerSrc;
        // pdf.js 6.x requires an options object -- a bare URL string is silently
        // read as {} and fails with "expected either `data`, `range`, or `url`".
        const pdf = await pdfjsLib.getDocument({ url: pdfUrl }).promise;
        container.innerHTML = '';

        // Pass 1: size every canvas up front, so the container reaches its final
        // height before anything renders -- rendering incrementally let the browser's
        // scroll anchoring drag scrollTop away from 0 as each page was appended (#109).
        const pages = [];
        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
            const page = await pdf.getPage(pageNumber);
            const targetWidth = container.clientWidth || 600;
            const scale = targetWidth / page.getViewport({ scale: 1 }).width;
            const viewport = page.getViewport({ scale: Math.max(scale, 0.1) });
            const canvas = document.createElement('canvas');
            canvas.className = 'document-viewer-pdf-page';
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            container.appendChild(canvas);
            pages.push({ canvas, page, viewport });
        }

        const stage = container.closest('.document-viewer-stage');
        if (stage) stage.scrollTop = 0;

        // Pass 2: render lazily as each page scrolls into view, instead of blocking
        // the first paint on every page of a long scanned document.
        const rendered = new WeakSet();
        const renderPage = async ({ canvas, page, viewport }) => {
            if (rendered.has(canvas)) return;
            rendered.add(canvas);
            const context = canvas.getContext('2d');
            await page.render({ canvasContext: context, viewport }).promise;
        };
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;
                    const target = pages.find(({ canvas }) => canvas === entry.target);
                    if (target) renderPage(target);
                });
            },
            { root: stage || null, rootMargin: '200px 0px' },
        );
        pages.forEach(({ canvas }) => observer.observe(canvas));
    } catch (error) {
        console.error('Échec du rendu PDF :', error);
        container.textContent = "Impossible d'afficher ce PDF ici. ";
        const link = document.createElement('a');
        link.href = `${pdfUrl}?download=1`;
        link.textContent = 'Télécharger le fichier';
        container.appendChild(link);
    }
}
