from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('crmChat', '0012_alter_channelintegration_channel_and_more')]

    operations = [
        migrations.AddField(
            model_name='crmcontact',
            name='last_interaction_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
