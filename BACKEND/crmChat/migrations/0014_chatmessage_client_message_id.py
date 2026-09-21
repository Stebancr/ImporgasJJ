from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('crmChat', '0013_crmcontact_last_interaction_at')]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='client_message_id',
            field=models.CharField(
                blank=True,
                help_text='Identificador idempotente generado por CRM o aplicación móvil.',
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
    ]
