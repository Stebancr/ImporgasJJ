"""Validación de mensajes reactivos y quick replies de Messenger."""

from rest_framework import serializers


class MessengerMessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, required=False)
    quick_replies = serializers.ListField(child=serializers.DictField(), required=False)
    attachment = serializers.DictField(required=False)

    def validate(self, attrs):
        if not attrs.get('text') and not attrs.get('attachment'):
            raise serializers.ValidationError('Se requiere texto o adjunto.')
        return attrs
