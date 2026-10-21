"""Permit the previous image to create accounts after an image-only rollback."""
from django.db import migrations


def retain_default(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        model = apps.get_model('usuarios', 'Credenciales')
        schema_editor.execute('ALTER TABLE %s ALTER COLUMN password_reset_version SET DEFAULT 0' %
                              schema_editor.quote_name(model._meta.db_table))


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0008_password_recovery_audit')]
    operations = [migrations.RunPython(retain_default, migrations.RunPython.noop)]
