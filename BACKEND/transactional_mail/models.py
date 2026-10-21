import uuid
from django.db import models


class Delivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=[('order', 'Compra aprobada'), ('visit', 'Visita finalizada')])
    object_id = models.PositiveBigIntegerField()
    recipient = models.EmailField(blank=True)
    state = models.CharField(max_length=20, default='pending', choices=[
        ('pending','Pendiente'), ('sending','Enviando'), ('sent','Enviado'), ('failed','Fallido'), ('uncertain','Revisar entrega'), ('cancelled','Cancelado')])
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    started_at = models.DateTimeField(null=True)
    next_attempt_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=200, blank=True)
    message_id = models.CharField(max_length=200, blank=True)
    provider_id = models.CharField(max_length=200, blank=True)
    document = models.FileField(upload_to='private_receipts/', blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['kind','object_id'], name='unique_transactional_event')]

