from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('crmChat', '0006_chatmessage_bot_claim')]
    operations = [
        migrations.AddField(model_name='chatsession', name='last_bot_message_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='chatsession', name='inactivity_warning_at', field=models.DateTimeField(blank=True, null=True)),
    ]
