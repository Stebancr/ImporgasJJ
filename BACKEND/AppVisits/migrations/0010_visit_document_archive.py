from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('AppVisits', '0009_visit_initial_final_cost')]

    operations = [
        migrations.AddField(model_name='visitatecnica', name='pdf_sha256', field=models.CharField(max_length=64, blank=True, default='')),
        migrations.AddField(model_name='visitatecnica', name='pdf_source_hash', field=models.CharField(max_length=64, blank=True, default='')),
        migrations.AddField(model_name='visitatecnica', name='pdf_bytes', field=models.PositiveBigIntegerField(null=True, blank=True)),
        migrations.AddField(model_name='visitatecnica', name='pdf_generado_en', field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name='visitatecnica', name='pdf_estado', field=models.CharField(max_length=20, blank=True, default='')),
        migrations.AddField(model_name='visitatecnica', name='pdf_error', field=models.CharField(max_length=300, blank=True, default='')),
        migrations.AddField(model_name='visitatecnica', name='pdf_link_version', field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name='evidenciafotografica', name='archivada_en', field=models.DateTimeField(null=True, blank=True)),
    ]
