document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input[type="password"]').forEach(initPasswordToggle);
});

function initPasswordToggle(input) {
    const wrapper = document.createElement('div');
    wrapper.className = 'input-group';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline-secondary';
    button.textContent = 'Afficher';
    button.setAttribute('aria-label', 'Afficher le mot de passe');
    button.setAttribute('aria-pressed', 'false');
    wrapper.appendChild(button);

    button.addEventListener('click', () => {
        const revealed = input.type === 'text';
        input.type = revealed ? 'password' : 'text';
        button.textContent = revealed ? 'Afficher' : 'Masquer';
        button.setAttribute('aria-label', revealed ? 'Afficher le mot de passe' : 'Masquer le mot de passe');
        button.setAttribute('aria-pressed', revealed ? 'false' : 'true');
    });
}
