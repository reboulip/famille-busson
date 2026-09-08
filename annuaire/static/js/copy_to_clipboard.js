(function () {
    document.querySelectorAll('[data-copy-target]').forEach((button) => {
        button.addEventListener('click', () => {
            const target = document.getElementById(button.dataset.copyTarget);
            if (!target) return;
            const text = target.value !== undefined ? target.value : target.textContent;
            const originalLabel = button.textContent;
            navigator.clipboard.writeText(text).then(() => {
                button.textContent = 'Copié !';
                setTimeout(() => {
                    button.textContent = originalLabel;
                }, 2000);
            });
        });
    });
})();
