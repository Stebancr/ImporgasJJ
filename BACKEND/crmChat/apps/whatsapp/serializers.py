"""Validación de envíos específicos de WhatsApp."""

from rest_framework import serializers


class WhatsAppInteractiveSerializer(serializers.Serializer):
    interactive = serializers.DictField()
