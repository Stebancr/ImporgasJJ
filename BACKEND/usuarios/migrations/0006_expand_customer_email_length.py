from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0005_usuario_terms_acceptance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='credenciales',
            name='usuario',
            field=models.CharField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='correo',
            field=models.CharField(blank=True, max_length=254, null=True),
        ),
    ]
