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
});

async function renderPdf(container) {
    const { pdfUrl, pdfjsSrc, pdfjsWorkerSrc } = container.dataset;
    try {
        const pdfjsLib = await import(pdfjsSrc);
        pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerSrc;
        const pdf = await pdfjsLib.getDocument(pdfUrl).promise;
        container.innerHTML = '';
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
            const context = canvas.getContext('2d');
            // eslint-disable-next-line no-await-in-loop -- pages must render in order
            await page.render({ canvasContext: context, viewport }).promise;
        }
    } catch (error) {
        console.error('Échec du rendu PDF :', error);
        container.textContent = "Impossible d'afficher ce PDF ici. ";
        const link = document.createElement('a');
        link.href = `${pdfUrl}?download=1`;
        link.textContent = 'Télécharger le fichier';
        container.appendChild(link);
    }
}
