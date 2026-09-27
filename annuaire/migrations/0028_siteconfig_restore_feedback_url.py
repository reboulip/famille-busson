from django.db import migrations

FEEDBACK_URL = "https://github.com/reboulip/famille-busson/issues/new"


def restore_feedback_url(apps, schema_editor):
    """Phase 18.1's seed migration (0023) set feedback_url to "" for every
    deployment, which silently hid the "Signaler un bug..." link from the menu
    (#153) -- the template only renders it when the field is truthy. This
    restores it, but only on the specific row 0023 itself seeded and that
    nobody has since touched: a harmless no-op everywhere else, including a
    fresh install (no Account rows yet) or a deployment where staff already
    set their own feedback_url or renamed the site.

    Side effects, both accepted: this bypasses the ORM, so annuaire/signals.py's
    site_config cache isn't invalidated (the link can take up to CACHE_TTL,
    300s, to appear after deploy) and no AuditEvent is recorded for the change.
    """
    SiteConfig = apps.get_model("annuaire", "SiteConfig")
    SiteConfig.objects.filter(pk=1, site_name="Famille Busson", feedback_url="").update(
        feedback_url=FEEDBACK_URL
    )


class Migration(migrations.Migration):
    dependencies = [
        ("annuaire", "0027_alter_relation_relationship_type"),
    ]

    operations = [
        migrations.RunPython(restore_feedback_url, migrations.RunPython.noop),
    ]
