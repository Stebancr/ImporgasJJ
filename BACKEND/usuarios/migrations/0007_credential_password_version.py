from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0006_expand_customer_email_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='credenciales',
            name='password_version',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
