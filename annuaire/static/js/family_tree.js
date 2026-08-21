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

    const initialMainId = container.dataset.mainId || (components.length > 0 ? components[0].root_id : null);
    if (!initialMainId) {
        container.textContent = "Aucune personne à centrer sur l'arbre.";
        return;
    }

    const byId = new Map(graph.map((person) => [person.id, person]));
    const detailPanel = document.getElementById('genealogie-detail');
    const branchPicker = document.getElementById('genealogie-branch-picker');

    function personLabel(person) {
        return `${person.data['first name']} ${person.data['last name']}`.trim();
    }

    function relationChipsHtml(ids, emptyText) {
        const known = ids.map((id) => byId.get(id)).filter(Boolean);
        if (known.length === 0) {
            return `<p class="genealogie-detail-empty">${emptyText}</p>`;
        }
        return known
            .map(
                (rel) =>
                    `<button type="button" class="btn btn-sm btn-outline-secondary genealogie-chip" data-person-id="${rel.id}">${personLabel(rel)}</button>`
            )
            .join(' ');
    }

    function showDetail(chart, person) {
        if (!detailPanel) return;
        const birthYear = person.data.birthday ? `<p>🎂 ${person.data.birthday}</p>` : '';
        detailPanel.innerHTML = `
            <div class="genealogie-detail-header">
                <img src="${person.data.avatar}" alt="" class="genealogie-detail-avatar">
                <h2>${personLabel(person)}</h2>
            </div>
            ${birthYear}
            <p>
                <a href="${person.data.url}" class="btn btn-sm btn-primary">Voir le profil complet</a>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-center-id="${person.id}">Centrer l'arbre ici</button>
            </p>
            <h3>Parents</h3>
            ${relationChipsHtml(person.rels.parents, 'Aucun parent renseigné.')}
            <h3>Conjoint·e(s)</h3>
            ${relationChipsHtml(person.rels.spouses, 'Aucun·e conjoint·e renseigné·e.')}
            <h3>Enfants</h3>
            ${relationChipsHtml(person.rels.children, 'Aucun enfant renseigné.')}
        `;
        detailPanel.classList.remove('d-none');

        detailPanel.querySelectorAll('[data-person-id]').forEach((button) => {
            button.addEventListener('click', () => {
                const rel = byId.get(button.dataset.personId);
                if (rel) showDetail(chart, rel);
            });
        });
        const centerButton = detailPanel.querySelector('[data-center-id]');
        if (centerButton) {
            centerButton.addEventListener('click', () => {
                chart.updateMainId(centerButton.dataset.centerId);
                chart.updateTree({ tree_position: 'main_to_middle' });
            });
        }
    }

    const mount = document.getElementById('genealogie-chart-mount') || container;
    const chart = f3.createChart(mount, graph);
    chart
        .setCardHtml()
        .setCardDisplay([['first name', 'last name'], ['birthday']])
        .setCardImageField('avatar')
        .setStyle('imageCircleRect')
        .setOnCardClick(function (e, d) {
            // d is family-chart's TreeDatum -- a D3-hierarchy-style wrapper
            // (depth/parent/children/x/y for layout) with the original datum
            // preserved intact under d.data, not spread onto d itself.
            // Synthetic placeholder cards (single-parent slots, "add" prompts)
            // carry no real person data -- clicking them must be a no-op.
            if (d.data.to_add || d.data.unknown || d.data._new_rel_data) return;
            showDetail(chart, d.data);
        });
    chart.setOrientationVertical();
    chart.setPersonDropdown(personLabel, { placeholder: 'Rechercher une personne…' });
    chart.setSingleParentEmptyCard(false);
    chart.setCardYSpacing(190);
    chart.updateMainId(initialMainId);
    chart.updateTree({ initial: true, tree_position: 'fit' });

    if (branchPicker && components.length > 1) {
        branchPicker.hidden = false;
        const options = ['<option value="">Changer de branche…</option>'].concat(
            components.map((component) => {
                const count = component.size > 1 ? `${component.size} personnes` : '1 personne';
                return `<option value="${component.root_id}">${component.label} (${count})</option>`;
            })
        );
        branchPicker.innerHTML = options.join('');
        branchPicker.addEventListener('change', () => {
            if (!branchPicker.value) return;
            chart.updateMainId(branchPicker.value);
            chart.updateTree({ tree_position: 'fit' });
            if (detailPanel) {
                detailPanel.classList.add('d-none');
                detailPanel.innerHTML = '<p class="genealogie-detail-empty">Sélectionnez une personne dans l\'arbre.</p>';
            }
        });
    }
});
