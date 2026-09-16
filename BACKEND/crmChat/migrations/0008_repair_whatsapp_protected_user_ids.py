from django.db import migrations


def repair_whatsapp_user_ids(apps, schema_editor):
    ChatMessage = apps.get_model('crmChat', 'ChatMessage')
    ChatSession = apps.get_model('crmChat', 'ChatSession')
    ChannelIdentity = apps.get_model('crmChat', 'ChannelIdentity')
    WebhookEvent = apps.get_model('crmChat', 'WebhookEvent')

    for webhook in WebhookEvent.objects.filter(channel='whatsapp').iterator():
        for entry in webhook.payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                for incoming in value.get('messages', []):
                    sender_id = str(incoming.get('from') or incoming.get('from_user_id') or '')
                    external_message_id = str(incoming.get('id') or '')
                    if not sender_id or not external_message_id:
                        continue
                    message = ChatMessage.objects.filter(
                        external_message_id=external_message_id,
                        session__external_thread_id='',
                    ).select_related('session').first()
                    if message is None:
                        continue
                    session = message.session
                    collision = ChatSession.objects.filter(
                        integration_id=session.integration_id,
                        external_thread_id=sender_id,
                    ).exclude(pk=session.pk).exists()
                    if collision:
                        continue
                    ChatSession.objects.filter(pk=session.pk, external_thread_id='').update(
                        external_thread_id=sender_id,
                        user_cedula=sender_id,
                    )
                    identity = ChannelIdentity.objects.filter(
                        integration_id=session.integration_id,
                        contact_id=session.contact_id,
                        external_id='',
                    ).first()
                    identity_collision = ChannelIdentity.objects.filter(
                        integration_id=session.integration_id,
                        external_id=sender_id,
                    ).exclude(pk=getattr(identity, 'pk', None)).exists()
                    if identity is not None and not identity_collision:
                        identity.external_id = sender_id
                        identity.save(update_fields=['external_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('crmChat', '0007_chatsession_inactivity_fields'),
    ]

    operations = [
        migrations.RunPython(repair_whatsapp_user_ids, migrations.RunPython.noop),
    ]
