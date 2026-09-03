// Compact horizontal card spacing (#81) -- vendor default is 250px. The
// genealogy label wraps instead of clipping (see main.css) and its max-width
// is derived from this spacing, not hardcoded separately, so the two can
// never drift out of the "label max-width <= spacing - 10" invariant that
// keeps adjacent labels from overlapping (see --genealogie-label-max-width
// in main.css). 170 was tuned against a deliberately long compound name in
// the dev-environment check required by #81's reopening -- don't lower it
// without re-running that check.
const CARD_X_SPACING = 170;
const LABEL_MAX_WIDTH = CARD_X_SPACING - 10;

// Image export (#113) resolution clamp. EXPORT_MAX_AREA is a hard ceiling, not just a
// size preference -- iOS Safari silently returns a blank "data:," image past ~16.7M
// px with no exception, so exceeding it produces a broken download, not just a big
// one. EXPORT_MAX_SIDE mirrors html-to-image's own canvas dimension limit (16384px),
// halved for headroom. EXPORT_MIN_PIXEL_RATIO is a floor -- a small tree must not
// export worse than before this fix.
const EXPORT_MAX_SIDE = 8192;
const EXPORT_MAX_AREA = 16e6;
const EXPORT_MIN_PIXEL_RATIO = 2;

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('genealogie-chart');
    if (!container) return;

    document.documentElement.style.setProperty(
        '--genealogie-label-max-width',
        `${LABEL_MAX_WIDTH}px`
    );

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

    // Layout-only hint for the vendor's spouse-side/children-sort logic (#81)
    // -- family-chart places a spouse to the right only when
    // data.gender === 'M', with no other hook available, and the same flag
    // drives its children-by-couple sort order. Stamped uniformly so it
    // fixes both halves of #81's "spouses come from the wrong side" without
    // meaning anything: never persisted, never sent to the server, never
    // displayed as a value anywhere (Person.gender was intentionally removed
    // from the data model, migration 0007, and must stay removed). The
    // matching main.css override neutralizes the vendor's blue-grey
    // card-male ring color so nothing on screen looks gendered.
    graph.forEach((person) => {
        person.data.gender = 'M';
    });

    const mount = document.getElementById('genealogie-chart-mount') || container;
    const chart = f3.createChart(mount, graph);
    chart
        .setCardHtml()
        .setCardDisplay([['first name'], ['last name'], ['birthday']])
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
    chart.setCardXSpacing(CARD_X_SPACING);
    chart.setOrientationVertical();
    chart.setPersonDropdown(personLabel, {
        cont: document.getElementById('genealogie-search') || undefined,
        placeholder: 'Rechercher une personne…',
    });
    chart.setSingleParentEmptyCard(false);
    // family-chart rebuilds .card_cont on every updateMainId/branch change, so a
    // one-shot class-stamp would be lost on the next render -- re-stamp after every
    // update instead, keyed off the same data-id the Excel export already reads.
    chart.setAfterUpdate(() => {
        mount.querySelectorAll('.card[data-id]').forEach((card) => {
            const person = byId.get(card.dataset.id);
            card.classList.toggle('card--deceased', Boolean(person && person.data.deceased));
        });
    });
    chart.updateMainId(initialMainId);
    chart.updateTree({ initial: true, tree_position: 'fit' });

    const exportButton = document.getElementById('genealogie-export');
    if (exportButton) {
        exportButton.addEventListener('click', () => {
            // "Currently rendered" = every real (non-placeholder) .card element
            // family-chart has drawn into the mount right now -- card-to-add/
            // card-unknown/card-new-rel mark synthetic cards with no real person
            // behind them (see the same check in setOnCardClick above).
            const ids = Array.from(mount.querySelectorAll('.card'))
                .filter(
                    (card) =>
                        !card.classList.contains('card-to-add') &&
                        !card.classList.contains('card-unknown') &&
                        !card.classList.contains('card-new-rel')
                )
                .map((card) => card.dataset.id)
                .filter(Boolean);
            if (ids.length === 0) return;
            const params = new URLSearchParams();
            ids.forEach((id) => params.append('ids', id));
            window.location.href = `${exportButton.dataset.exportUrl}?${params.toString()}`;
        });
    }

    function exportTreeImage(exportChart, exportMount, button) {
        // Always fit-then-capture -- never the as-displayed viewport, which may be
        // panned/zoomed to only part of the tree. transition_time: 0 makes the fit
        // instantaneous instead of the default ~1000ms d3 zoom transition -- the old
        // single-rAF capture below could otherwise land mid-transition (#113).
        exportChart.updateTree({ tree_position: 'fit', transition_time: 0 });
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Génération…';

        // Two rAFs: the tree update itself needs a frame to reflow, and a
        // zero-duration d3 transition still only applies on the *next* timer tick.
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                // The relationship connector lines carry their color as an inline
                // SVG stroke attribute (vendor default, white) that main.css's
                // `.f3 .link { stroke: #6c757d }` overrides on screen -- but
                // html-to-image clones the <svg> subtree raw, without inlining any
                // computed style, so the export used to capture the vendor's
                // original white-on-white lines. Stamp each link's *computed*
                // stroke onto its own inline style just before capture (read, never
                // hardcoded, so CSS stays the single source of truth), and restore
                // it afterward so the live tree is never visually altered.
                const links = Array.from(mount.querySelectorAll('.link'));
                const savedStyles = links.map((link) => link.getAttribute('style'));
                links.forEach((link) => {
                    const stroke = window.getComputedStyle(link).stroke;
                    link.style.stroke = stroke;
                    link.style.opacity = '1';
                });

                // Resolution (#113): derive pixelRatio from how much the fit actually
                // shrank the tree, not from the viewer's screen density -- a large
                // branch fits at a small scale, so a fixed pixelRatio produced
                // unreadably small cards regardless of screen. Read the scale the
                // vendor just wrote onto the cards layer's transform.
                const cardsView = mount.querySelector('#htmlSvg .cards_view');
                const transform = cardsView ? cardsView.style.transform : '';
                const scaleMatch = /scale\(([\d.]+)\)/.exec(transform);
                const fitScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1;
                const rect = mount.getBoundingClientRect();
                const width = rect.width || 1;
                const height = rect.height || 1;
                const pixelRatio = clamp(
                    fitScale > 0 ? 1 / fitScale : EXPORT_MIN_PIXEL_RATIO,
                    EXPORT_MIN_PIXEL_RATIO,
                    Math.min(EXPORT_MAX_SIDE / width, EXPORT_MAX_SIDE / height, Math.sqrt(EXPORT_MAX_AREA / (width * height)))
                );

                htmlToImage
                    .toJpeg(exportMount, {
                        backgroundColor: '#ffffff',
                        pixelRatio,
                        quality: 0.92,
                        skipFonts: true,
                    })
                    .then((dataUrl) => {
                        const today = new Date().toISOString().slice(0, 10);
                        const link = document.createElement('a');
                        link.download = `genealogie-${today}.jpg`;
                        link.href = dataUrl;
                        link.click();
                    })
                    .catch((error) => {
                        console.error("Échec de l'export en image :", error);
                    })
                    .finally(() => {
                        links.forEach((link, i) => {
                            if (savedStyles[i] === null) {
                                link.removeAttribute('style');
                            } else {
                                link.setAttribute('style', savedStyles[i]);
                            }
                        });
                        button.disabled = false;
                        button.textContent = originalText;
                    });
            });
        });
    }

    const exportImageButton = document.getElementById('genealogie-export-image');
    if (exportImageButton && window.htmlToImage) {
        exportImageButton.addEventListener('click', () => exportTreeImage(chart, mount, exportImageButton));
    }

    const fullscreenPanel = document.getElementById('genealogie-panel');
    const fullscreenButton = document.getElementById('genealogie-fullscreen');
    if (fullscreenPanel && fullscreenButton) {
        const setFullscreen = (active) => {
            fullscreenPanel.classList.toggle('genealogie-panel--fullscreen', active);
            fullscreenButton.textContent = active ? 'Quitter le plein écran' : 'Plein écran';
            // family-chart has no resize/ResizeObserver handler -- it computes its
            // fit from getBoundingClientRect() at call time, so the re-fit must
            // wait a frame for the size/position change to actually reflow.
            requestAnimationFrame(() => chart.updateTree({ tree_position: 'fit' }));
        };
        fullscreenButton.addEventListener('click', () => {
            setFullscreen(!fullscreenPanel.classList.contains('genealogie-panel--fullscreen'));
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && fullscreenPanel.classList.contains('genealogie-panel--fullscreen')) {
                setFullscreen(false);
            }
        });
    }

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
