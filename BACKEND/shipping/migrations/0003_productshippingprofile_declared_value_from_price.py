from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shipping', '0002_shippingquote_provider_summary')]
    operations = [migrations.AddField(model_name='productshippingprofile', name='declared_value_from_price',
                                     field=models.BooleanField(default=False))]
