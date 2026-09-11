"""Alias tipado del webhook para Facebook Messenger."""

from crmChat.apps.meta.views import MetaWebhookView


class FacebookWebhookView(MetaWebhookView):
    forced_channel = 'facebook'
