from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0004_credenciales_location')]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='terms_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='terms_version',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
