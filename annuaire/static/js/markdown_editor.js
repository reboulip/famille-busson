function initMarkdownEditors() {
    document.querySelectorAll('.markdown-editor').forEach(initEditor);
}

// One transform per toolbar action. "wrap" surrounds the selection (or a placeholder,
// pre-selected so typing replaces it) with before/after text. "line-prefix" prefixes
// every line touched by the selection (or just the current line) -- used for headings,
// quotes and lists, which are block-level in Markdown, not inline.
const MARKDOWN_TOOLBAR_ACTIONS = {
    heading: { mode: 'line-prefix', prefix: '## ' },
    bold: { mode: 'wrap', before: '**', after: '**', placeholder: 'texte en gras' },
    italic: { mode: 'wrap', before: '*', after: '*', placeholder: 'texte en italique' },
    quote: { mode: 'line-prefix', prefix: '> ' },
    code: { mode: 'wrap', before: '`', after: '`', placeholder: 'code' },
    link: { mode: 'wrap', before: '[', after: '](https://)', placeholder: 'texte du lien' },
    ul: { mode: 'line-prefix', prefix: '- ' },
    ol: { mode: 'line-prefix', prefix: '1. ' },
};

function insertTextPreservingUndo(textarea, text) {
    textarea.focus();
    // execCommand keeps the browser's native undo stack intact; reassigning the
    // textarea's value directly would silently wipe it.
    if (!document.execCommand('insertText', false, text)) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        textarea.setRangeText(text, start, end, 'end');
    }
    // The preview debounce below listens for 'input', which programmatic edits don't
    // fire on their own.
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
}

function applyMarkdownToolbarAction(textarea, actionName) {
    const action = MARKDOWN_TOOLBAR_ACTIONS[actionName];
    if (!action) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.slice(start, end);

    if (action.mode === 'wrap') {
        const text = selected || action.placeholder;
        insertTextPreservingUndo(textarea, action.before + text + action.after);
        if (!selected) {
            const placeholderStart = start + action.before.length;
            textarea.setSelectionRange(placeholderStart, placeholderStart + action.placeholder.length);
        }
        return;
    }

    const lineStart = textarea.value.lastIndexOf('\n', start - 1) + 1;
    const nextBreak = textarea.value.indexOf('\n', end);
    const lineEnd = nextBreak === -1 ? textarea.value.length : nextBreak;
    const block = textarea.value.slice(lineStart, lineEnd);
    const prefixed = block
        .split('\n')
        .map((line) => action.prefix + line)
        .join('\n');
    textarea.setSelectionRange(lineStart, lineEnd);
    insertTextPreservingUndo(textarea, prefixed);
}

function initEditor(editor) {
    if (editor.dataset.initialized === 'true') return;
    editor.dataset.initialized = 'true';

    const previewUrl = editor.dataset.previewUrl;
    const textarea = editor.querySelector('textarea');
    const writePane = editor.querySelector('.markdown-editor-write');
    const previewPane = editor.querySelector('.markdown-editor-preview');
    const toolbar = editor.querySelector('.markdown-editor-toolbar');
    const tabs = editor.querySelectorAll('.markdown-editor-tab');
    if (!textarea || !writePane || !previewPane) return;

    const form = editor.closest('form');
    const csrfInput = form ? form.querySelector('input[name=csrfmiddlewaretoken]') : null;

    let debounceTimer = null;

    function activateTab(name) {
        tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
        writePane.hidden = name !== 'write';
        previewPane.hidden = name !== 'preview';
        if (toolbar) toolbar.hidden = name !== 'write';
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

    if (toolbar) {
        toolbar.querySelectorAll('[data-md-action]').forEach((button) => {
            button.addEventListener('click', () => {
                applyMarkdownToolbarAction(textarea, button.dataset.mdAction);
            });
        });
    }

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
