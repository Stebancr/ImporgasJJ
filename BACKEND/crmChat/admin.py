"""Administración interna del CRM omnicanal.

Los secretos de Meta se excluyen deliberadamente de listados y formularios del
admin de Django. La configuración sensible se gestiona mediante la API protegida
que cifra los valores antes de persistirlos.
"""

from django.contrib import admin

from .models import (
    AssignmentQueue,
    ChannelIdentity,
    ChannelIntegration,
    ChatAttachment,
    ChatAuditEvent,
    ChatMessage,
    ChatSession,
    CRMContact,
    MetaConnection,
    MetaFacebookPage,
    MetaInstagramAccount,
    QueueMember,
    WebhookEvent,
)


@admin.register(CRMContact)
class CRMContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'updated_at')
    search_fields = ('name', 'phone', 'email')


@admin.register(ChannelIntegration)
class ChannelIntegrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'channel', 'active', 'external_account_id', 'updated_at')
    list_filter = ('channel', 'active')
    search_fields = ('name', 'external_account_id', 'phone_number_id', 'page_id')
    exclude = ('access_token_encrypted', 'app_secret_encrypted', 'verify_token_digest')


@admin.register(MetaConnection)
class MetaConnectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'facebook_user_id', 'created_by', 'token_status', 'is_active', 'updated_at')
    list_filter = ('token_status', 'is_active')
    readonly_fields = ('facebook_user_id', 'granted_scopes', 'token_created_at', 'token_expires_at', 'token_last_validated_at')
    exclude = ('access_token_encrypted',)


@admin.register(MetaFacebookPage)
class MetaFacebookPageAdmin(admin.ModelAdmin):
    list_display = ('id', 'page_name', 'page_id', 'connection', 'is_selected', 'is_active')
    list_filter = ('is_selected', 'is_active')
    exclude = ('page_access_token_encrypted',)


@admin.register(MetaInstagramAccount)
class MetaInstagramAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'instagram_account_id', 'facebook_page', 'is_selected', 'is_active')
    list_filter = ('is_selected', 'is_active')


@admin.register(ChannelIdentity)
class ChannelIdentityAdmin(admin.ModelAdmin):
    list_display = ('id', 'contact', 'integration', 'external_id', 'updated_at')
    search_fields = ('external_id', 'display_name', 'contact__name')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_name', 'channel', 'status', 'priority', 'agent_name', 'updated_at')
    list_filter = ('channel', 'status', 'priority')
    search_fields = ('user_name', 'user_cedula', 'external_thread_id')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender_type', 'direction', 'message_type', 'status', 'created_at')
    list_filter = ('sender_type', 'direction', 'message_type', 'status')
    search_fields = ('text', 'external_message_id')


admin.site.register(ChatAttachment)
admin.site.register(AssignmentQueue)
admin.site.register(QueueMember)
admin.site.register(WebhookEvent)
admin.site.register(ChatAuditEvent)
