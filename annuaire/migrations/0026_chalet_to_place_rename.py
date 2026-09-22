import django.db.models.deletion
from django.db import migrations, models
from django.utils.translation import pgettext_lazy


class Migration(migrations.Migration):
    """Phase 16.1 -- Chalet/PresencePSV become the generic Place/Stay pair.

    Hand-written as RenameModel/RenameField/AlterField only -- this runs against
    a live Postgres database and must never drop/recreate the tables (the
    autodetector's default answer to "did you rename this model?" is "no" when
    run non-interactively, which produces a destructive delete+create instead;
    do not regenerate this file with a plain `makemigrations`).
    """

    dependencies = [
        ('annuaire', '0025_account_language'),
    ]

    operations = [
        migrations.RenameModel(old_name='Chalet', new_name='Place'),
        migrations.RenameModel(old_name='PresencePSV', new_name='Stay'),
        migrations.RenameField(model_name='stay', old_name='chalet', new_name='place'),
        migrations.AlterField(
            model_name='place',
            name='name',
            field=models.CharField(max_length=100, verbose_name=pgettext_lazy('place', 'Nom')),
        ),
        migrations.AlterField(
            model_name='place',
            name='owners',
            field=models.ManyToManyField(
                blank=True, related_name='owned_places', to='annuaire.person', verbose_name='Propriétaires'
            ),
        ),
        migrations.AlterField(
            model_name='stay',
            name='person',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stays',
                to='annuaire.person',
                verbose_name='Personne',
            ),
        ),
        migrations.AlterField(
            model_name='stay',
            name='place',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to='annuaire.place', verbose_name='Lieu'
            ),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='place_label_singular',
            field=models.CharField(
                blank=True, default='', max_length=50, verbose_name='Libellé (singulier) des lieux'
            ),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='place_label_plural',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Libellé (pluriel) des lieux'),
        ),
    ]
