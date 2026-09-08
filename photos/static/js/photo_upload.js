function initPhotoUploads() {
    document.querySelectorAll('[data-photo-upload]').forEach(initPhotoUpload);
}

function initPhotoUpload(container) {
    const picker = container.querySelector('[data-photo-picker]');
    const addBtn = container.querySelector('[data-photo-upload-trigger]');
    const list = container.querySelector('[data-photo-upload-list]');
    const csrfInput = container.querySelector('input[name=csrfmiddlewaretoken]');
    if (!picker || !addBtn || !list || !csrfInput) return;

    const uploadUrl = container.dataset.uploadUrl;
    const maxFiles = parseInt(container.dataset.maxFiles, 10);
    const maxBytes = parseInt(container.dataset.maxBytes, 10);
    const maxConcurrent = parseInt(container.dataset.maxConcurrent, 10) || 1;

    addBtn.addEventListener('click', () => picker.click());

    picker.addEventListener('change', () => {
        const files = Array.from(picker.files);
        picker.value = '';
        if (files.length > maxFiles) {
            window.alert('Vous ne pouvez sélectionner que ' + maxFiles + ' fichiers maximum.');
            return;
        }
        queueUploads(files);
    });

    function queueUploads(files) {
        const queue = files.slice();
        let activeCount = 0;

        function runNext() {
            while (activeCount < maxConcurrent && queue.length > 0) {
                const file = queue.shift();
                activeCount += 1;
                uploadFile(file).finally(() => {
                    activeCount -= 1;
                    runNext();
                });
            }
        }

        runNext();
    }

    function buildRow(filename) {
        const row = document.createElement('li');
        row.className = 'photo-upload-row';
        const name = document.createElement('span');
        name.className = 'photo-upload-row__name';
        name.textContent = filename;
        const progress = document.createElement('progress');
        progress.className = 'photo-upload-row__progress';
        progress.max = 100;
        progress.value = 0;
        const status = document.createElement('span');
        status.className = 'photo-upload-row__status fb-meta';
        row.appendChild(name);
        row.appendChild(progress);
        row.appendChild(status);
        list.appendChild(row);
        return { row, name, progress, status };
    }

    function markDone(rowParts, data) {
        rowParts.progress.remove();
        rowParts.status.textContent = 'Ajoutée';
        rowParts.row.classList.add('photo-upload-row--done');
        if (data.thumbnail_url) {
            const img = document.createElement('img');
            img.src = data.thumbnail_url;
            img.className = 'photo-upload-row__thumbnail';
            rowParts.row.insertBefore(img, rowParts.name);
        }
    }

    function markError(rowParts, message) {
        rowParts.progress.remove();
        rowParts.status.textContent = message;
        rowParts.row.classList.add('photo-upload-row--error');
    }

    function uploadFile(file) {
        const rowParts = buildRow(file.name);

        if (file.size > maxBytes) {
            markError(rowParts, 'Fichier trop volumineux.');
            return Promise.resolve();
        }

        return new Promise((resolve) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', uploadUrl);
            xhr.setRequestHeader('X-CSRFToken', csrfInput.value);

            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    rowParts.progress.value = Math.round((event.loaded / event.total) * 100);
                }
            });

            xhr.addEventListener('load', () => {
                let data = {};
                try {
                    data = JSON.parse(xhr.responseText);
                } catch (err) {
                    data = {};
                }
                if (xhr.status >= 200 && xhr.status < 300 && !data.error) {
                    markDone(rowParts, data);
                } else {
                    markError(rowParts, data.error || "Échec de l'envoi.");
                }
                resolve();
            });

            xhr.addEventListener('error', () => {
                markError(rowParts, "Échec de l'envoi.");
                resolve();
            });

            const formData = new FormData();
            formData.append('file', file);
            xhr.send(formData);
        });
    }
}

document.addEventListener('DOMContentLoaded', initPhotoUploads);
if (document.readyState !== 'loading') {
    initPhotoUploads();
}
