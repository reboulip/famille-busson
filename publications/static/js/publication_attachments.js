(function () {
    const form = document.getElementById('blogpost-form');
    if (!form) return;

    const rowsContainer = form.querySelector('.attachment-formset-rows');
    const badgesContainer = document.getElementById('attachment-badges');
    const addBtn = document.getElementById('add-attachment-btn');
    const picker = document.getElementById('attachment-picker');
    const template = document.getElementById('attachment-row-template');
    if (!rowsContainer || !badgesContainer || !addBtn || !picker || !template) return;

    const totalInput = form.querySelector('input[name="attachments-TOTAL_FORMS"]');
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
        badge.className = 'badge bg-secondary me-1 mb-1 attachment-badge';

        const label = document.createElement('span');
        label.className = 'attachment-badge-name';
        label.textContent = displayName;
        badge.appendChild(label);

        const captionInput = findField(row, 'caption');
        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'btn btn-sm btn-link p-0 ms-2 attachment-badge-edit text-white';
        editBtn.setAttribute('aria-label', 'Modifier la légende');
        editBtn.textContent = '✎';
        badge.appendChild(editBtn);

        const captionField = document.createElement('input');
        captionField.type = 'text';
        captionField.className = 'form-control form-control-sm attachment-badge-caption ms-2';
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
        const rows = rowsContainer.querySelectorAll('.attachment-row');
        rows.forEach((row, idx) => {
            row.querySelectorAll('[name]').forEach((el) => {
                el.name = el.name.replace(/attachments-\d+-/, 'attachments-' + idx + '-');
                if (el.id) el.id = el.id.replace(/attachments-\d+-/, 'attachments-' + idx + '-');
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
        const rows = rowsContainer.querySelectorAll('.attachment-row');
        rows.forEach((row) => {
            const isExisting = row.dataset.existing === '1';
            if (!isExisting) return;
            const name = existingFilename(row) || 'Pièce jointe';
            makeBadge(row, name);
        });
    }

    addBtn.addEventListener('click', () => picker.click());

    picker.addEventListener('change', () => {
        Array.from(picker.files).forEach(addRowForFile);
        picker.value = '';
    });

    const postTypeField = form.querySelector('[name="post_type"]');
    form.addEventListener('submit', (e) => {
        if (!postTypeField || postTypeField.value !== 'BC') return;
        const visibleBadges = badgesContainer.querySelectorAll('.attachment-badge').length;
        const existingNotDeleted = Array.from(rowsContainer.querySelectorAll('.attachment-row'))
            .filter((row) => {
                const del = findField(row, 'DELETE');
                return !del || !del.checked;
            }).length;
        if (visibleBadges === 0 && existingNotDeleted === 0) {
            const ok = window.confirm(
                "Cette publication est de type « Busson Connection » mais ne contient aucune pièce jointe. " +
                "Voulez-vous l'enregistrer quand même ?"
            );
            if (!ok) {
                e.preventDefault();
            }
        }
    });

    initExistingRows();
})();
