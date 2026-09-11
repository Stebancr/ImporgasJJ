"""Validación de mensajes y quick replies de Instagram."""

from crmChat.apps.facebook.serializers import MessengerMessageSerializer


class InstagramMessageSerializer(MessengerMessageSerializer):
    """Instagram comparte la forma básica de mensajes con Messenger."""
