from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0023_north_location_pin')]
    operations = [migrations.AddField(
        model_name='category', name='icon_key',
        field=models.CharField(blank=True, default=None, max_length=64, null=True,
                               verbose_name='Icono seleccionado'),
    )]
