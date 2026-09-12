from django.db import migrations


def seed_site_config(apps, schema_editor):
    """Seeds the current site identity only if this deployment already has
    Account rows -- i.e. only on an existing (production) database. A fresh
    checkout or test database gets pure model defaults instead, per Phase 16's
    goal of a reusable, generically-branded fresh install."""
    Account = apps.get_model("annuaire", "Account")
    SiteConfig = apps.get_model("annuaire", "SiteConfig")
    if not Account.objects.exists():
        return
    SiteConfig.objects.get_or_create(
        pk=1,
        defaults={
            "site_name": "Famille Busson",
            # \N{NO-BREAK SPACE} (U+00A0), not a plain space -- the &nbsp;
            # entity in emails/_wordmark.html gets replaced by this stored
            # literal character in 15.2.
            "wordmark": "Famille\N{NO-BREAK SPACE}Busson",
            "tagline": "",
            "sender_address": "",
            "feedback_url": "",
            "timezone": "Europe/Paris",
            "default_language": "",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("annuaire", "0022_siteconfig"),
    ]

    operations = [
        migrations.RunPython(seed_site_config, migrations.RunPython.noop),
    ]
