(function () {
    const form = document.getElementById('document-form');
    if (!form) return;

    const rowsContainer = form.querySelector('.document-file-formset-rows');
    const badgesContainer = document.getElementById('document-file-badges');
    const addBtn = document.getElementById('add-document-file-btn');
    const picker = document.getElementById('document-file-picker');
    const template = document.getElementById('document-file-row-template');
    if (!rowsContainer || !badgesContainer || !addBtn || !picker || !template) return;

    const totalInput = form.querySelector('input[name="files-TOTAL_FORMS"]');
    if (!totalInput) return;

    function findField(row, suffix) {
        return row.querySelector('[name$="-' + suffix + '"]');
    }

    function existingFilename(row) {
        const fileInput = findField(row, 'file');
        if (!fileInput) return null;
        const sibling = fileInput.parentElement.querySelector('a');
        if (sibling && sibling.textContent.trim()) return sibling.textContent.trim();
        const initial = fileInput.getAttribute('data-initial');
        if (initial) return initial.split('/').pop();
        return null;
    }

    function makeBadge(row, displayName) {
        const badge = document.createElement('span');
        badge.className = 'fb-chip me-1 mb-1 document-file-badge';

        const label = document.createElement('span');
        label.className = 'document-file-badge-name';
        label.textContent = displayName;
        badge.appendChild(label);

        const captionInput = findField(row, 'caption');
        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'btn btn-sm btn-link p-0 ms-2 document-file-badge-edit text-white';
        editBtn.setAttribute('aria-label', 'Modifier la légende');
        editBtn.textContent = '✎';
        badge.appendChild(editBtn);

        const captionField = document.createElement('input');
        captionField.type = 'text';
        captionField.className = 'form-control form-control-sm document-file-badge-caption ms-2';
        captionField.placeholder = 'Légende (optionnel)';
        captionField.value = captionInput ? captionInput.value : '';
        captionField.hidden = !captionField.value;
        captionField.addEventListener('input', () => {
            if (captionInput) captionInput.value = captionField.value;
        });
        badge.appendChild(captionField);

        editBtn.addEventListener('click', () => {
            captionField.hidden = !captionField.hidden;
            if (!captionField.hidden) captionField.focus();
        });

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white btn-close-sm ms-2';
        closeBtn.setAttribute('aria-label', 'Retirer ' + displayName);
        closeBtn.addEventListener('click', () => removeRow(row, badge));
        badge.appendChild(closeBtn);

        badgesContainer.appendChild(badge);
        return badge;
    }

    function removeRow(row, badge) {
        const isExisting = row.dataset.existing === '1';
        if (isExisting) {
            const deleteField = findField(row, 'DELETE');
            if (deleteField) deleteField.checked = true;
        } else {
            row.remove();
            totalInput.value = String(parseInt(totalInput.value, 10) - 1);
            reindexRows();
        }
        badge.remove();
    }

    function reindexRows() {
        const rows = rowsContainer.querySelectorAll('.document-file-row');
        rows.forEach((row, idx) => {
            row.querySelectorAll('[name]').forEach((el) => {
                el.name = el.name.replace(/files-\d+-/, 'files-' + idx + '-');
                if (el.id) el.id = el.id.replace(/files-\d+-/, 'files-' + idx + '-');
            });
        });
    }

    function addRowForFile(file) {
        const idx = parseInt(totalInput.value, 10);
        const html = template.innerHTML.replace(/__prefix__/g, String(idx));
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html.trim();
        const row = wrapper.firstElementChild;
        rowsContainer.appendChild(row);

        const fileInput = findField(row, 'file');
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;

        totalInput.value = String(idx + 1);
        makeBadge(row, file.name);
    }

    function initExistingRows() {
        const rows = rowsContainer.querySelectorAll('.document-file-row');
        rows.forEach((row) => {
            const isExisting = row.dataset.existing === '1';
            if (!isExisting) return;
            const name = existingFilename(row) || 'Fichier';
            makeBadge(row, name);
        });
    }

    const MAX_FILES_PER_SELECTION = 100;

    addBtn.addEventListener('click', () => picker.click());

    picker.addEventListener('change', () => {
        if (picker.files.length > MAX_FILES_PER_SELECTION) {
            window.alert('Vous ne pouvez sélectionner que ' + MAX_FILES_PER_SELECTION + ' fichiers maximum.');
            picker.value = '';
            return;
        }
        Array.from(picker.files).forEach(addRowForFile);
        picker.value = '';
    });

    initExistingRows();
})();
