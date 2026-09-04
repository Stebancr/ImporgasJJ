# Generated manually to preserve existing persistent data.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ecommerce', '0010_fcmdevicetoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_confirmation_email_sent_at',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='Correo de pago confirmado enviado'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_confirmation_email_error',
            field=models.TextField(blank=True, editable=False, verbose_name='Error de correo de pago confirmado'),
        ),
    ]
