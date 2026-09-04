from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('crmChat', '0002_alter_chatmessage_id_alter_chatsession_id')]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='conversation_state',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='conversation_summary',
            field=models.TextField(blank=True, default=''),
        ),
    ]
