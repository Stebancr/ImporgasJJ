"""Alias tipado del webhook para instalaciones separadas de WhatsApp."""

from crmChat.apps.meta.views import MetaWebhookView


class WhatsAppWebhookView(MetaWebhookView):
    forced_channel = 'whatsapp'
