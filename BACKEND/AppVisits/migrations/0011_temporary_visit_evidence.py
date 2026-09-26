from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('AppVisits', '0010_visit_document_archive')]

    operations = [
        migrations.AlterField(
            model_name='evidenciafotografica', name='imagen',
            field=models.ImageField(upload_to='evidencias_temporales/', blank=True),
        ),
        migrations.AddField(
            model_name='evidenciafotografica', name='es_temporal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='evidenciafotografica', name='eliminada_en',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
