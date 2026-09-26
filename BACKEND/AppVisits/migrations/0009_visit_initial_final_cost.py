from django.db import migrations, models
from django.db.models import Q


def preserve_initial_cost(apps, schema_editor):
    Visit = apps.get_model('AppVisits', 'VisitaTecnica')
    Change = apps.get_model('AppVisits', 'CambioCostoVisita')
    for visit in Visit.objects.using(schema_editor.connection.alias).iterator():
        first = (Change.objects.using(schema_editor.connection.alias)
                 .filter(visita_id=visit.pk).order_by('cambiado_en', 'pk').first())
        if first and first.valor_anterior is not None:
            initial = first.valor_anterior
        elif (first and first.usuario_id == visit.creado_por_id and visit.creado_por_id
              and abs((first.cambiado_en - visit.fecha_creacion).total_seconds()) < 300):
            # Registro inicial generado al crear la visita, no una modificación del técnico.
            initial = first.valor_nuevo
        elif first:
            initial = None
        else:
            # En una visita finalizada sin auditoría no se puede reconstruir
            # con seguridad el valor original. Se conserva solo su valor final.
            initial = visit.valor_visita if visit.estado in ('pendiente', 'en_proceso') else None
        Visit.objects.using(schema_editor.connection.alias).filter(pk=visit.pk).update(costo_inicial=initial)


class Migration(migrations.Migration):
    dependencies = [('AppVisits', '0008_visit_pdf_delivery')]

    operations = [
        migrations.AddField(
            model_name='visitatecnica', name='costo_inicial',
            field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='cambiocostovisita', name='motivo',
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(preserve_initial_cost, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='visitatecnica',
            constraint=models.CheckConstraint(
                condition=Q(costo_inicial__gte=0) | Q(costo_inicial__isnull=True),
                name='visita_costo_inicial_no_negativo',
            ),
        ),
    ]
