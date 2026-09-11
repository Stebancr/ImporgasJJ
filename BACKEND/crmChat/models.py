"""Modelos persistentes del CRM y de la bandeja omnicanal.

Los modelos originales ``ChatSession`` y ``ChatMessage`` se conservan para no
romper el chat del ecommerce ni sus tablas.  Los campos omnicanal son aditivos:
una conversación antigua sigue siendo válida y se considera del canal
``ecommerce``.
"""

from django.conf import settings
from django.db import models


class CRMContact(models.Model):
    """Persona normalizada que puede escribir desde uno o varios canales."""

    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='crm_contacts',
    )
    name = models.CharField(max_length=200, default='Cliente')
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    avatar_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_contact'
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class ChannelIntegration(models.Model):
    """Cuenta externa configurada para recibir y enviar mensajes.

    Los secretos se guardan cifrados por ``crmChat.meta.services``. Nunca se
    deben serializar ni mostrar nuevamente desde la API administrativa.
    """

    CHANNEL_ECOMMERCE = 'ecommerce'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_FACEBOOK = 'facebook'
    CHANNEL_INSTAGRAM = 'instagram'
    CHANNEL_CHOICES = [
        (CHANNEL_ECOMMERCE, 'Ecommerce'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_FACEBOOK, 'Facebook Messenger'),
        (CHANNEL_INSTAGRAM, 'Instagram'),
    ]

    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    active = models.BooleanField(default=False)
    app_id = models.CharField(max_length=120, blank=True)
    external_account_id = models.CharField(max_length=255, blank=True)
    phone_number_id = models.CharField(max_length=120, blank=True)
    page_id = models.CharField(max_length=120, blank=True)
    instagram_account_id = models.CharField(max_length=120, blank=True)
    graph_api_version = models.CharField(max_length=20, blank=True)
    access_token_encrypted = models.TextField(blank=True)
    app_secret_encrypted = models.TextField(blank=True)
    verify_token_digest = models.CharField(max_length=64, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_channel_integrations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_channel_integration'
        ordering = ['channel', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['channel', 'external_account_id'],
                condition=~models.Q(external_account_id=''),
                name='crm_unique_channel_external_account',
            ),
        ]

    def __str__(self):
        return f'{self.get_channel_display()}: {self.name}'


class ChannelIdentity(models.Model):
    """Identificador de un contacto dentro de una cuenta y canal concretos."""

    contact = models.ForeignKey(
        CRMContact,
        on_delete=models.CASCADE,
        related_name='channel_identities',
    )
    integration = models.ForeignKey(
        ChannelIntegration,
        on_delete=models.CASCADE,
        related_name='contact_identities',
    )
    external_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=200, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_channel_identity'
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'external_id'],
                name='crm_unique_integration_identity',
            ),
        ]

    def __str__(self):
        return f'{self.integration.channel}:{self.external_id}'


class AssignmentQueue(models.Model):
    """Cola de atención utilizada para asignación manual o automática."""

    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)
    auto_assign = models.BooleanField(default=False)
    channels = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_assignment_queue'
        ordering = ['name']

    def __str__(self):
        return self.name


class QueueMember(models.Model):
    """Asesor habilitado para recibir conversaciones de una cola."""

    queue = models.ForeignKey(
        AssignmentQueue,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='crm_queue_memberships',
    )
    active = models.BooleanField(default=True)
    capacity = models.PositiveSmallIntegerField(default=10)

    class Meta:
        db_table = 'crm_queue_member'
        constraints = [
            models.UniqueConstraint(
                fields=['queue', 'user'],
                name='crm_unique_queue_member',
            ),
        ]


class ChatSession(models.Model):
    """Conversación unificada, compatible con el chat del ecommerce."""

    STATUS_CHOICES = [
        ('bot',     'Con bot'),
        ('waiting', 'Esperando agente'),
        ('active',  'Con agente'),
        ('closed',  'Cerrado'),
    ]

    user_id_ref    = models.IntegerField(null=True, blank=True)          # Credenciales.id
    user_name      = models.CharField(max_length=200, default='Usuario')
    user_cedula    = models.CharField(max_length=50, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='bot')
    agent_id_ref   = models.IntegerField(null=True, blank=True)          # Credenciales.id of agent
    agent_name     = models.CharField(max_length=200, blank=True)
    unread_by_agent = models.IntegerField(default=0)                     # messages not yet seen by agent
    conversation_state = models.JSONField(default=dict, blank=True)
    conversation_summary = models.TextField(blank=True, default='')
    contact = models.ForeignKey(
        CRMContact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
    )
    integration = models.ForeignKey(
        ChannelIntegration,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
    )
    channel = models.CharField(
        max_length=20,
        choices=ChannelIntegration.CHANNEL_CHOICES,
        default=ChannelIntegration.CHANNEL_ECOMMERCE,
        db_index=True,
    )
    external_thread_id = models.CharField(max_length=255, blank=True, db_index=True)
    priority = models.CharField(
        max_length=12,
        choices=[('low', 'Baja'), ('normal', 'Normal'), ('high', 'Alta'), ('urgent', 'Urgente')],
        default='normal',
        db_index=True,
    )
    queue = models.ForeignKey(
        AssignmentQueue,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_crm_conversations',
    )
    last_customer_message_at = models.DateTimeField(null=True, blank=True)
    last_agent_message_at = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_chat_session'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['channel', 'status', '-updated_at'], name='crm_session_channel_status'),
            models.Index(fields=['queue', 'priority', '-updated_at'], name='crm_session_queue_priority'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['integration', 'external_thread_id'],
                condition=~models.Q(external_thread_id=''),
                name='crm_unique_external_thread',
            ),
        ]

    def __str__(self):
        return f"Session {self.id} — {self.user_name} ({self.status})"


class ChatMessage(models.Model):
    """Mensaje normalizado entrante, saliente o generado por el bot."""

    SENDER_TYPES = [
        ('user',  'Usuario'),
        ('bot',   'Bot'),
        ('agent', 'Agente'),
    ]

    session     = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    text        = models.TextField()
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    sender_name = models.CharField(max_length=200, blank=True)
    direction = models.CharField(
        max_length=10,
        choices=[('inbound', 'Entrante'), ('outbound', 'Saliente'), ('internal', 'Interno')],
        default='internal',
        db_index=True,
    )
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Texto'),
            ('image', 'Imagen'),
            ('audio', 'Audio'),
            ('video', 'Video'),
            ('document', 'Documento'),
            ('sticker', 'Sticker'),
            ('template', 'Plantilla'),
            ('interactive', 'Interactivo'),
        ],
        default='text',
    )
    external_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('received', 'Recibido'),
            ('queued', 'En cola'),
            ('sent', 'Enviado'),
            ('delivered', 'Entregado'),
            ('read', 'Leído'),
            ('failed', 'Fallido'),
        ],
        default='received',
        db_index=True,
    )
    external_timestamp = models.DateTimeField(null=True, blank=True)
    reply_to_external_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm_chat_message'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type}] {self.text[:60]}"


class ChatAttachment(models.Model):
    """Archivo vinculado a un mensaje y guardado en el media existente."""

    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(upload_to='crm_chat/%Y/%m/', blank=True)
    external_media_id = models.CharField(max_length=255, blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=150, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm_chat_attachment'


class WebhookEvent(models.Model):
    """Evento Meta idempotente; el payload nunca debe contener tokens."""

    event_key = models.CharField(max_length=255, unique=True)
    channel = models.CharField(max_length=20, choices=ChannelIntegration.CHANNEL_CHOICES)
    integration = models.ForeignKey(
        ChannelIntegration,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='webhook_events',
    )
    payload = models.JSONField(default=dict)
    payload_sha256 = models.CharField(max_length=64)
    status = models.CharField(
        max_length=20,
        choices=[('received', 'Recibido'), ('processing', 'Procesando'), ('processed', 'Procesado'), ('failed', 'Fallido')],
        default='received',
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'crm_webhook_event'
        ordering = ['-received_at']


class ChatAuditEvent(models.Model):
    """Auditoría sin secretos de acciones sensibles del CRM."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='crm_audit_events',
    )
    session = models.ForeignKey(
        ChatSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_events',
    )
    action = models.CharField(max_length=80, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm_chat_audit_event'
        ordering = ['-created_at']
