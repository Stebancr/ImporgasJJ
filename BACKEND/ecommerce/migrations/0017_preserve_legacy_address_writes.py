from django.db import migrations


def allow_legacy_address_writes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    table = apps.get_model('ecommerce', 'UserAddress')._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(cursor, table)
    if any(column.name == 'tcc_city_code' for column in columns):
        schema_editor.execute('ALTER TABLE %s ALTER COLUMN tcc_city_code SET DEFAULT %s' %
                              (schema_editor.quote_name(table), "''"))


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0016_producteditoroperation')]
    operations = [migrations.RunPython(allow_legacy_address_writes, migrations.RunPython.noop)]
