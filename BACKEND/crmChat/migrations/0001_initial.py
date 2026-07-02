import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id',              models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('user_id_ref',     models.IntegerField(blank=True, null=True)),
                ('user_name',       models.CharField(default='Usuario', max_length=200)),
                ('user_cedula',     models.CharField(blank=True, max_length=50)),
                ('status',          models.CharField(
                    choices=[('bot','Con bot'),('waiting','Esperando agente'),('active','Con agente'),('closed','Cerrado')],
                    default='bot', max_length=20,
                )),
                ('agent_id_ref',    models.IntegerField(blank=True, null=True)),
                ('agent_name',      models.CharField(blank=True, max_length=200)),
                ('unread_by_agent', models.IntegerField(default=0)),
                ('created_at',      models.DateTimeField(auto_now_add=True)),
                ('updated_at',      models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'crm_chat_session', 'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id',          models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('session',     models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='crmChat.chatsession',
                )),
                ('text',        models.TextField()),
                ('sender_type', models.CharField(
                    choices=[('user','Usuario'),('bot','Bot'),('agent','Agente')],
                    max_length=10,
                )),
                ('sender_name', models.CharField(blank=True, max_length=200)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'crm_chat_message', 'ordering': ['created_at']},
        ),
    ]
