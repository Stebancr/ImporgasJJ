"""Validación de envíos específicos de WhatsApp."""

from rest_framework import serializers


class WhatsAppTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=512)
    language_code = serializers.CharField(max_length=35)
    components = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class WhatsAppInteractiveSerializer(serializers.Serializer):
    interactive = serializers.DictField()
