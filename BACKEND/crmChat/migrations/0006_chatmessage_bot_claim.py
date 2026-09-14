from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('crmChat', '0005_metaconnection_channelintegration_meta_connection_and_more')]
    operations = [
        migrations.AddField(
            model_name='chatmessage', name='bot_processing_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage', name='reply_to_message',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bot_reply', to='crmChat.chatmessage'),
        ),
    ]

