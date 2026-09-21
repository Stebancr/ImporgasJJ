from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('AppVisits', '0005_visitatecnica_valor_visita_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visitatecnica',
            name='tipo_tarea',
            field=models.CharField(max_length=50, choices=[
                ('visita_urbana', 'VISITA TECNICA PERIMETRO URBANO'),
                ('instalacion_calentador', '2025 INSTALACION DE CALENTADOR'),
                ('mantenimiento_calentador', '2025 MANTENIMIENTO O REPARACION DE CALENTADOR'),
                ('instalacion_secadora', '2025 INSTALACION DE SECADORA'),
                ('servicio_cancelado', 'SERVICIO CANCELADO'),
                ('visita_afueras', 'VISITA TECNICA PERIMETRO URBANO AFUERAS'),
                ('mantenimiento_estufa', '2025 MANTENIMIENTO O REPARACION DE ESTUFA'),
                ('revision_periodica', 'REVISION PERIODICA'),
                ('mantenimiento_acumulacion', '2025 MANTENIMIENTO O REPARACION CALENTADOR DE ACUMULACION A GAS'),
                ('programacion_doble', 'PROGRAMACION DOBLE'),
                ('mantenimiento_turco', '2025 MANTENIMIENTO O REPARACION CALENTADOR DE TURCO DE PASO'),
            ]),
        ),
    ]
