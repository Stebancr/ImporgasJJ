import uuid
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class ProductShippingProfile(models.Model):
    """Uniform boxes per sale unit; dimensions/weight refer to EACH box."""
    product = models.OneToOneField('ecommerce.Product', on_delete=models.CASCADE, related_name='shipping_profile')
    requires_shipping = models.BooleanField(default=True)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(Decimal('0.001'))])
    height_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    width_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    length_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    packages_per_unit = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    # Documented class code. Fragility is internal; no undocumented TCC field is sent.
    packaging_code = models.CharField(max_length=30, default='CLEM_CAJA', choices=[('CLEM_CAJA', 'Caja'), ('CLEM_MEDIANA', 'Mediana')])
    fragile = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class ShippingQuote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64, db_index=True)
    snapshot = models.JSONField()
    environment = models.CharField(max_length=12)
    account_type = models.CharField(max_length=3)
    tcc_rate = models.DecimalField(max_digits=12, decimal_places=2)
    surcharge = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=200, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Shipment(models.Model):
    class State(models.TextChoices):
        AWAITING_PAYMENT = 'awaiting_payment', 'Pendiente de pago'
        PENDING = 'pending', 'Pendiente de crear en TCC'
        CREATING = 'creating', 'Creación en curso'
        CREATED = 'created', 'Despacho creado'
        ERROR = 'error', 'Error de creación'
        UNCERTAIN = 'uncertain', 'Confirmación pendiente de TCC'

    order = models.OneToOneField('ecommerce.Order', on_delete=models.PROTECT, related_name='shipment')
    quote = models.OneToOneField(ShippingQuote, on_delete=models.PROTECT)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    state = models.CharField(max_length=24, choices=State.choices, default=State.AWAITING_PAYMENT, db_index=True)
    waybill = models.CharField(max_length=100, blank=True, unique=True, null=True)
    pickup_number = models.CharField(max_length=100, blank=True)
    document_urls = models.JSONField(default=dict, blank=True)
    request_summary = models.JSONField(default=dict, blank=True)
    response_summary = models.JSONField(default=dict, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ShipmentEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name='events')
    event_key = models.CharField(max_length=100)
    state = models.CharField(max_length=24)
    description = models.CharField(max_length=300)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['shipment', 'event_key'], name='shipping_unique_event')]
        ordering = ['created_at', 'pk']
