document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('genealogie-chart');
    if (!container) return;

    let graph;
    let components;
    try {
        graph = JSON.parse(container.dataset.graph || '[]');
        components = JSON.parse(container.dataset.components || '[]');
    } catch (e) {
        container.textContent = "Impossible d'afficher l'arbre généalogique (données invalides).";
        return;
    }

    if (graph.length === 0) {
        container.textContent = 'Aucun profil à afficher pour le moment.';
        return;
    }

    const mainId = container.dataset.mainId || (components.length > 0 ? components[0].root_id : null);
    if (!mainId) {
        container.textContent = 'Aucune personne à centrer sur l\'arbre.';
        return;
    }

    const chart = f3.createChart(container, graph);
    chart
        .setCardHtml()
        .setCardDisplay([['first name', 'last name'], ['birthday']])
        .setCardImageField('avatar')
        .setStyle('imageCircleRect');
    chart.setOrientationVertical();
    chart.updateMainId(mainId);
    chart.updateTree({ initial: true });
});
