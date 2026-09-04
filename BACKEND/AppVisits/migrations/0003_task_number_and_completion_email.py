from django.db import migrations, models


def normalize_task_numbers(apps, schema_editor):
    Visit = apps.get_model('AppVisits', 'VisitaTecnica')
    for visit in Visit.objects.only('id', 'numero_tarea').iterator():
        expected = str(999 + visit.id)
        if visit.numero_tarea != expected:
            Visit.objects.filter(pk=visit.pk).update(numero_tarea=expected)


class Migration(migrations.Migration):
    dependencies = [('AppVisits', '0002_reportevisita_firma_base64')]

    operations = [
        migrations.AlterField(
            model_name='visitatecnica', name='numero_tarea',
            field=models.CharField(blank=True, editable=False, max_length=20, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='visitatecnica', name='correo_completada_en',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='visitatecnica', name='correo_completada_error',
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.RunPython(normalize_task_numbers, migrations.RunPython.noop),
    ]
