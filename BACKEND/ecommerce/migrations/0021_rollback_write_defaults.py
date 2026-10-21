"""Keep the previous release able to insert rows during image-only rollback."""
from django.db import migrations


def retain_defaults(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for model_name, names in [
        ('UserAddress', ('complement', 'neighborhood', 'delivery_instructions')),
        ('Order', ('discounts', 'taxes', 'delivery_details')),
        ('WompiPaymentIntent', ('discounts', 'taxes')),
    ]:
        model = apps.get_model('ecommerce', model_name)
        for name in names:
            field = model._meta.get_field(name)
            value = field.get_db_prep_save(field.get_default(), schema_editor.connection)
            schema_editor.execute('ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %%s' % (
                schema_editor.quote_name(model._meta.db_table), schema_editor.quote_name(field.column)), [value])


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0020_order_shipping_subsidy')]
    operations = [migrations.RunPython(retain_defaults, migrations.RunPython.noop)]
