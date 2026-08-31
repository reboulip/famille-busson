function initMarkdownEditors() {
    document.querySelectorAll('.markdown-editor').forEach(initEditor);
}

function initEditor(editor) {
    if (editor.dataset.initialized === 'true') return;
    editor.dataset.initialized = 'true';

    const previewUrl = editor.dataset.previewUrl;
    const textarea = editor.querySelector('textarea');
    const writePane = editor.querySelector('.markdown-editor-write');
    const previewPane = editor.querySelector('.markdown-editor-preview');
    const tabs = editor.querySelectorAll('.markdown-editor-tab');
    if (!textarea || !writePane || !previewPane) return;

    const form = editor.closest('form');
    const csrfInput = form ? form.querySelector('input[name=csrfmiddlewaretoken]') : null;

    let debounceTimer = null;

    function activateTab(name) {
        tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
        writePane.hidden = name !== 'write';
        previewPane.hidden = name !== 'preview';
        if (name === 'preview') fetchPreview();
    }

    function fetchPreview() {
        const text = textarea.value;
        if (!text.trim()) {
            previewPane.innerHTML = '<p class="markdown-editor-empty text-muted">Rien à prévisualiser.</p>';
            return;
        }
        if (!csrfInput) return;
        fetch(previewUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfInput.value,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'text=' + encodeURIComponent(text),
        })
            .then((r) => (r.ok ? r.text() : Promise.reject(r)))
            .then((html) => {
                previewPane.innerHTML = html;
            })
            .catch(() => {
                previewPane.innerHTML = '<p class="text-danger">Erreur lors du chargement de l’aperçu.</p>';
            });
    }

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => activateTab(tab.dataset.tab));
    });

    textarea.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            if (!previewPane.hidden) fetchPreview();
        }, 400);
    });
}

document.addEventListener('DOMContentLoaded', initMarkdownEditors);
if (document.readyState !== 'loading') {
    initMarkdownEditors();
}
