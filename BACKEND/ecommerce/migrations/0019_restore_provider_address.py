"""Restore provider state without overwriting published migrations or old codes."""
from django.db import migrations, models


def ensure_column(apps, schema_editor):
    model = apps.get_model('ecommerce', 'UserAddress')
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(cursor, model._meta.db_table)
    if not any(column.name == 'tcc_city_code' for column in columns):
        schema_editor.add_field(model, model._meta.get_field('tcc_city_code'))
    if schema_editor.connection.vendor == 'postgresql':
        # Older general-dev models omit this column. Keep their writes compatible.
        schema_editor.execute("ALTER TABLE %s ALTER COLUMN tcc_city_code SET DEFAULT ''" %
                              schema_editor.quote_name(model._meta.db_table))


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0018_delivery_without_shipping')]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.AddField(
                model_name='useraddress', name='tcc_city_code',
                field=models.CharField(max_length=8, blank=True, default=''),
            )],
            database_operations=[],
        ),
        migrations.RunPython(ensure_column, migrations.RunPython.noop),
    ]
