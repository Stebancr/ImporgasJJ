from decimal import Decimal

from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def identify_north(apps, schema_editor):
    locations = apps.get_model('ecommerce', 'Location').objects.using(schema_editor.connection.alias)
    matches = list(locations.annotate(label=Lower(Trim('name')), municipality=Lower(Trim('city')))
                   .filter(label__in=('norte', 'sede norte', 'sede cali norte', 'imporgas jj norte', 'imporgas jj | cali norte'),
                           municipality__in=('cali', 'santiago de cali')).values_list('pk', flat=True)[:2])
    if len(matches) > 1:
        raise RuntimeError('Hay más de una sede Norte en Cali. Identifica el registro antes de migrar.')
    if matches:
        locations.filter(pk=matches[0]).update(
            address='Av. 6 Norte #30N-46, piso 1, San Vicente',
            latitude=Decimal('3.4718433'),
            longitude=Decimal('-76.5266492'),
            google_place_id='ChIJXf6b2uupMI4RNN6J4-rm_jo',
        )


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0022_store_categories')]
    operations = [
        migrations.AddField('location', 'latitude', models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)),
        migrations.AddField('location', 'longitude', models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)),
        migrations.AddField('location', 'google_place_id', models.CharField(max_length=255, blank=True, default='')),
        migrations.RunPython(identify_north, migrations.RunPython.noop),
    ]
