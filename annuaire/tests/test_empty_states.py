from django.template import Context, Template

_TEMPLATE = Template(
    "{% include 'annuaire/_empty.html' with "
    "title=title body=body action_url=action_url action_label=action_label "
    "empty_hint=empty_hint empty_secondary_url=empty_secondary_url empty_secondary_label=empty_secondary_label %}"
)


def _render(**context):
    base = {
        "title": "",
        "body": "",
        "action_url": "",
        "action_label": "",
        "empty_hint": "",
        "empty_secondary_url": "",
        "empty_secondary_label": "",
    }
    base.update(context)
    return _TEMPLATE.render(Context(base))


def test_title_only():
    html = _render(title="Aucune chose")
    assert "Aucune chose" in html
    assert "fb-empty__hint" not in html
    assert "fb-empty__secondary" not in html


def test_hint_renders_when_provided():
    html = _render(title="Aucune chose", empty_hint="Commencez par…")
    assert '<p class="fb-empty__hint">Commencez par…</p>' in html


def test_secondary_action_requires_both_url_and_label():
    html = _render(title="Aucune chose", empty_secondary_url="/quelque-part/")
    assert "fb-empty__secondary" not in html


def test_secondary_action_renders_when_both_provided():
    html = _render(title="Aucune chose", empty_secondary_url="/annuaire/", empty_secondary_label="Voir tout")
    assert 'class="fb-empty__secondary"' in html
    assert '<a class="fb-btn fb-btn--quiet" href="/annuaire/">Voir tout</a>' in html


def test_primary_and_secondary_actions_coexist():
    html = _render(
        title="Aucune chose",
        action_url="/creer/",
        action_label="Créer",
        empty_secondary_url="/voir/",
        empty_secondary_label="Voir tout",
    )
    assert 'class="fb-empty__action"' in html
    assert 'class="fb-empty__secondary"' in html


def test_unset_optional_params_render_nothing():
    html = _render(title="Aucune chose")
    assert "fb-empty__hint" not in html
    assert "fb-empty__action" not in html
    assert "fb-empty__secondary" not in html
