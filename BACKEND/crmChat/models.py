from django.db import models


class ChatSession(models.Model):
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
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm_chat_session'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.id} — {self.user_name} ({self.status})"


class ChatMessage(models.Model):
    SENDER_TYPES = [
        ('user',  'Usuario'),
        ('bot',   'Bot'),
        ('agent', 'Agente'),
    ]

    session     = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    text        = models.TextField()
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    sender_name = models.CharField(max_length=200, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm_chat_message'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type}] {self.text[:60]}"
