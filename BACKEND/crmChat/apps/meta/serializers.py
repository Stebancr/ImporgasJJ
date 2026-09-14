"""Serializadores administrativos de integraciones Meta.

Los campos secretos son solamente de escritura. Las respuestas revelan si un
secreto existe, pero nunca su contenido cifrado o en texto plano.
"""

from rest_framework import serializers

from crmChat.models import (
    ChannelIntegration,
    ChatAuditEvent,
    MetaConnection,
    MetaFacebookPage,
    MetaInstagramAccount,
)

from .services import SecretConfigurationError, secret_store


class ChannelIntegrationSerializer(serializers.ModelSerializer):
    access_token = serializers.CharField(write_only=True, required=False, allow_blank=False)
    app_secret = serializers.CharField(write_only=True, required=False, allow_blank=False)
    verify_token = serializers.CharField(write_only=True, required=False, allow_blank=False)
    has_access_token = serializers.SerializerMethodField()
    has_app_secret = serializers.SerializerMethodField()
    has_verify_token = serializers.SerializerMethodField()
    managed_by_meta_oauth = serializers.SerializerMethodField()

    class Meta:
        model = ChannelIntegration
        fields = (
            'id', 'name', 'channel', 'active', 'app_id', 'external_account_id',
            'phone_number_id', 'page_id', 'instagram_account_id',
            'graph_api_version', 'configuration', 'token_expires_at',
            'access_token', 'app_secret', 'verify_token', 'has_access_token',
            'has_app_secret', 'has_verify_token', 'managed_by_meta_oauth',
            'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_has_access_token(self, obj):
        """Indica disponibilidad sin exponer el token ni su origen cifrado."""

        if obj.access_token_encrypted:
            return True
        if obj.meta_facebook_page_id:
            return bool(
                obj.meta_facebook_page.page_access_token_encrypted
                or obj.meta_facebook_page.connection.access_token_encrypted
            )
        return bool(obj.meta_connection_id and obj.meta_connection.access_token_encrypted)

    def get_has_app_secret(self, obj):
        return bool(obj.app_secret_encrypted)

    def get_has_verify_token(self, obj):
        return bool(obj.verify_token_digest)

    def get_managed_by_meta_oauth(self, obj):
        """Las cuentas descubiertas por Facebook Login no usan OAuth legado."""

        return bool(obj.meta_connection_id or obj.meta_facebook_page_id)

    def validate(self, attrs):
        channel = attrs.get('channel', getattr(self.instance, 'channel', None))
        active = attrs.get('active', getattr(self.instance, 'active', False))
        effective = lambda name: attrs.get(name, getattr(self.instance, name, ''))
        token_present = bool(attrs.get('access_token')) or bool(
            self.instance and self.instance.access_token_encrypted
        ) or bool(self.instance and self.instance.meta_facebook_page_id)

        if channel == ChannelIntegration.CHANNEL_ECOMMERCE:
            raise serializers.ValidationError({'channel': 'Ecommerce no requiere una integración Meta.'})
        if active and not effective('graph_api_version'):
            raise serializers.ValidationError({'graph_api_version': 'Es obligatorio al activar el canal.'})
        if active and not token_present:
            raise serializers.ValidationError({'access_token': 'Es obligatorio al activar el canal.'})
        if channel == ChannelIntegration.CHANNEL_WHATSAPP and active and not effective('phone_number_id'):
            raise serializers.ValidationError({'phone_number_id': 'Es obligatorio para WhatsApp.'})
        if channel == ChannelIntegration.CHANNEL_FACEBOOK and active and not effective('page_id'):
            raise serializers.ValidationError({'page_id': 'Es obligatorio para Messenger.'})
        if channel == ChannelIntegration.CHANNEL_INSTAGRAM and active and not effective('instagram_account_id'):
            raise serializers.ValidationError({'instagram_account_id': 'Es obligatorio para Instagram.'})
        return attrs

    def _save_secrets(self, instance, secrets):
        changed = []
        try:
            if secrets.get('access_token'):
                instance.access_token_encrypted = secret_store.encrypt(secrets['access_token'])
                changed.append('access_token_encrypted')
            if secrets.get('app_secret'):
                instance.app_secret_encrypted = secret_store.encrypt(secrets['app_secret'])
                changed.append('app_secret_encrypted')
            if secrets.get('verify_token'):
                instance.verify_token_digest = secret_store.digest(secrets['verify_token'])
                changed.append('verify_token_digest')
        except SecretConfigurationError as exc:
            raise serializers.ValidationError({'secrets': str(exc)}) from exc
        if changed:
            instance.save(update_fields=changed + ['updated_at'])
        return instance

    def _audit(self, instance, action, changed_fields, changed_secrets):
        """Registra la acción sin copiar valores sensibles a la auditoría."""

        request = self.context.get('request')
        ChatAuditEvent.objects.create(
            actor=getattr(request, 'user', None),
            action=action,
            details={
                'integration_id': instance.id,
                'channel': instance.channel,
                'changed_fields': sorted(changed_fields),
                'rotated_secrets': sorted(changed_secrets),
            },
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
        )

    def create(self, validated_data):
        secrets = {name: validated_data.pop(name, None) for name in ('access_token', 'app_secret', 'verify_token')}
        changed_fields = set(validated_data)
        validated_data['created_by'] = self.context['request'].user
        instance = super().create(validated_data)
        instance = self._save_secrets(instance, secrets)
        self._audit(instance, 'integration.created', changed_fields, [key for key, value in secrets.items() if value])
        return instance

    def update(self, instance, validated_data):
        secrets = {name: validated_data.pop(name, None) for name in ('access_token', 'app_secret', 'verify_token')}
        changed_fields = set(validated_data)
        instance = super().update(instance, validated_data)
        instance = self._save_secrets(instance, secrets)
        self._audit(instance, 'integration.updated', changed_fields, [key for key, value in secrets.items() if value])
        return instance


class MetaInstagramAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaInstagramAccount
        fields = ('instagram_account_id', 'username', 'name', 'profile_picture_url', 'is_selected', 'is_active')
        read_only_fields = fields


class MetaFacebookPageSerializer(serializers.ModelSerializer):
    instagram_account = MetaInstagramAccountSerializer(read_only=True)

    class Meta:
        model = MetaFacebookPage
        fields = ('page_id', 'page_name', 'tasks', 'is_selected', 'is_active', 'instagram_account')
        read_only_fields = fields


class MetaConnectionSerializer(serializers.ModelSerializer):
    facebook_pages = MetaFacebookPageSerializer(many=True, read_only=True)

    class Meta:
        model = MetaConnection
        fields = (
            'id', 'facebook_user_id', 'granted_scopes', 'token_created_at',
            'token_expires_at', 'token_last_validated_at', 'token_status',
            'is_active', 'facebook_pages', 'created_at', 'updated_at',
        )
        read_only_fields = fields


class MetaAccountSelectionSerializer(serializers.Serializer):
    facebook_page_ids = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
        default=list,
    )
    instagram_account_ids = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        attrs['facebook_page_ids'] = list(dict.fromkeys(attrs['facebook_page_ids']))
        attrs['instagram_account_ids'] = list(dict.fromkeys(attrs['instagram_account_ids']))
        if not attrs['facebook_page_ids'] and not attrs['instagram_account_ids']:
            raise serializers.ValidationError('Seleccione al menos una página o cuenta de Instagram.')
        return attrs
