from decimal import Decimal
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────
#  COTIZACION  (Quotation)
# ─────────────────────────────────────────────────────────────

class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        ('borrador',   'Borrador'),
        ('enviada',    'Enviada'),
        ('aprobada',   'Aprobada'),
        ('rechazada',  'Rechazada'),
        ('vencida',    'Vencida'),
        ('convertida', 'Convertida a Factura'),
    ]

    numero            = models.CharField(max_length=40, unique=True, blank=True, verbose_name="Número")
    location          = models.ForeignKey(
        'ecommerce.Location',
        on_delete=models.PROTECT,
        related_name='cotizaciones',
        verbose_name="Sede",
    )
    creado_por        = models.ForeignKey(
        'usuarios.Credenciales',
        on_delete=models.PROTECT,
        related_name='cotizaciones',
        verbose_name="Creado por",
    )

    # Client snapshot (can be a registered customer or walk-in)
    cliente_nombre    = models.CharField(max_length=200, verbose_name="Nombre cliente")
    cliente_cedula    = models.CharField(max_length=30, blank=True, verbose_name="Cédula")
    cliente_correo    = models.CharField(max_length=254, blank=True, verbose_name="Correo")
    cliente_telefono  = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")

    estado            = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    fecha_emision     = models.DateField(auto_now_add=True, verbose_name="Fecha emisión")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha vencimiento")

    # Totals — recalculated from items
    subtotal          = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Subtotal")
    descuento_pct     = models.DecimalField(max_digits=5,  decimal_places=2, default=0, verbose_name="Descuento %")
    descuento_monto   = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Descuento $")
    impuesto_pct      = models.DecimalField(max_digits=5,  decimal_places=2, default=0, verbose_name="Impuesto %")
    impuesto_monto    = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Impuesto $")
    total             = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Total")

    notas             = models.TextField(blank=True, verbose_name="Notas")
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cotizaciones'
        ordering = ['-created_at']
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero:
            year = timezone.now().year
            self.numero = f"COT-{self.location_id}-{year}-{self.pk:06d}"
            Cotizacion.objects.filter(pk=self.pk).update(numero=self.numero)

    def recalcular_totales(self):
        subtotal = sum(item.subtotal for item in self.items.all()) or Decimal('0')
        descuento_monto = (subtotal * self.descuento_pct / 100).quantize(Decimal('0.01'))
        base = subtotal - descuento_monto
        impuesto_monto = (base * self.impuesto_pct / 100).quantize(Decimal('0.01'))
        Cotizacion.objects.filter(pk=self.pk).update(
            subtotal=subtotal,
            descuento_monto=descuento_monto,
            impuesto_monto=impuesto_monto,
            total=base + impuesto_monto,
        )
        self.refresh_from_db()

    def __str__(self):
        return f"{self.numero} — {self.cliente_nombre}"


class CotizacionItem(models.Model):
    cotizacion      = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='items')
    producto        = models.ForeignKey(
        'ecommerce.Product',
        on_delete=models.PROTECT,
        verbose_name="Producto",
    )
    descripcion     = models.CharField(max_length=255, verbose_name="Descripción")
    cantidad        = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio unitario")
    descuento_item  = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Descuento línea $")
    subtotal        = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Subtotal", editable=False)

    class Meta:
        db_table = 'cotizacion_items'
        verbose_name = 'Ítem cotización'
        verbose_name_plural = 'Ítems cotización'

    def save(self, *args, **kwargs):
        self.subtotal = (self.precio_unitario * self.cantidad) - self.descuento_item
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.descripcion} x{self.cantidad}"


# ─────────────────────────────────────────────────────────────
#  FACTURA  (Invoice)
# ─────────────────────────────────────────────────────────────

class Factura(models.Model):
    ESTADO_CHOICES = [
        ('emitida', 'Emitida'),
        ('anulada', 'Anulada'),
    ]

    numero           = models.CharField(max_length=40, unique=True, blank=True, verbose_name="Número")
    cotizacion       = models.OneToOneField(
        Cotizacion,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='factura',
        verbose_name="Cotización origen",
    )
    location         = models.ForeignKey(
        'ecommerce.Location',
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name="Sede",
    )
    creado_por       = models.ForeignKey(
        'usuarios.Credenciales',
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name="Creado por",
    )

    cliente_nombre   = models.CharField(max_length=200, verbose_name="Nombre cliente")
    cliente_cedula   = models.CharField(max_length=30, blank=True, verbose_name="Cédula")
    cliente_correo   = models.CharField(max_length=254, blank=True, verbose_name="Correo")
    cliente_telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")

    estado           = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='emitida')
    fecha_emision    = models.DateField(auto_now_add=True, verbose_name="Fecha emisión")

    subtotal         = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento_pct    = models.DecimalField(max_digits=5,  decimal_places=2, default=0)
    descuento_monto  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impuesto_pct     = models.DecimalField(max_digits=5,  decimal_places=2, default=0)
    impuesto_monto   = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total            = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    notas            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'facturas'
        ordering = ['-created_at']
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero:
            year = timezone.now().year
            self.numero = f"FAC-{self.location_id}-{year}-{self.pk:06d}"
            Factura.objects.filter(pk=self.pk).update(numero=self.numero)

    def recalcular_totales(self):
        subtotal = sum(item.subtotal for item in self.items.all()) or Decimal('0')
        descuento_monto = (subtotal * self.descuento_pct / 100).quantize(Decimal('0.01'))
        base = subtotal - descuento_monto
        impuesto_monto = (base * self.impuesto_pct / 100).quantize(Decimal('0.01'))
        Factura.objects.filter(pk=self.pk).update(
            subtotal=subtotal,
            descuento_monto=descuento_monto,
            impuesto_monto=impuesto_monto,
            total=base + impuesto_monto,
        )
        self.refresh_from_db()

    def __str__(self):
        return f"{self.numero} — {self.cliente_nombre}"


class FacturaItem(models.Model):
    factura         = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items')
    producto        = models.ForeignKey(
        'ecommerce.Product',
        on_delete=models.PROTECT,
        verbose_name="Producto",
    )
    descripcion     = models.CharField(max_length=255, verbose_name="Descripción")
    cantidad        = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio unitario")
    descuento_item  = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Descuento línea $")
    subtotal        = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Subtotal", editable=False)

    class Meta:
        db_table = 'factura_items'
        verbose_name = 'Ítem factura'
        verbose_name_plural = 'Ítems factura'

    def save(self, *args, **kwargs):
        self.subtotal = (self.precio_unitario * self.cantidad) - self.descuento_item
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.descripcion} x{self.cantidad}"

