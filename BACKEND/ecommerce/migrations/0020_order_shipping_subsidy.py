from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0019_restore_provider_address')]
    operations = [
        migrations.AddField(model_name='order', name='carrier_shipping_cost', field=models.DecimalField(blank=True, null=True, max_digits=14, decimal_places=2)),
        migrations.AddField(model_name='order', name='shipping_discount', field=models.DecimalField(blank=True, null=True, max_digits=14, decimal_places=2)),
        migrations.AddField(model_name='order', name='free_shipping_applied', field=models.BooleanField(blank=True, null=True)),
        migrations.AddField(model_name='order', name='free_shipping_threshold', field=models.DecimalField(blank=True, null=True, max_digits=14, decimal_places=2)),
    ]
