"""Parser de eventos ``messaging`` de Instagram."""

from crmChat.apps.meta.webhooks import parse_messaging_entries


def parse_webhook(payload):
    return parse_messaging_entries(payload, 'instagram')
