"""
Modelos de Ecommerce — adaptados del diseño PostgreSQL en backendee/models.py
Compatible con SQLite (tests) y PostgreSQL (producción/dev).
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# ─────────────────────────────────────────────
#  BRAND
# ─────────────────────────────────────────────

class Brand(models.Model):
    name        = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    logo        = models.URLField(max_length=500, blank=True, default='', verbose_name="Logo URL")
    description = models.TextField(blank=True, verbose_name="Descripción")
    is_active   = models.BooleanField(default=True, verbose_name="Activa")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  LOCATION  (punto físico / bodega)
# ─────────────────────────────────────────────

class Location(models.Model):
    name             = models.CharField(max_length=150, unique=True, verbose_name="Nombre")
    address          = models.TextField(verbose_name="Dirección")
    city             = models.CharField(max_length=100, verbose_name="Ciudad")
    phone            = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    hours_weekday    = models.CharField(max_length=50, blank=True, default='', verbose_name="Horario L-V")
    hours_saturday   = models.CharField(max_length=50, blank=True, default='', verbose_name="Horario Sábado")
    hours_sunday     = models.CharField(max_length=50, blank=True, default='', verbose_name="Horario Domingo")
    is_active        = models.BooleanField(default=True, verbose_name="Activa")
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'locations'
        ordering = ['city', 'name']
        verbose_name = 'Punto físico'
        verbose_name_plural = 'Puntos físicos'

    def __str__(self):
        return f"{self.name} — {self.city}"


# ─────────────────────────────────────────────
#  CATEGORY
# ─────────────────────────────────────────────

class Category(models.Model):
    name        = models.CharField(max_length=100, verbose_name="Nombre")
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    icon        = models.CharField(max_length=100, blank=True, verbose_name="Icono")
    description = models.TextField(blank=True, verbose_name="Descripción")
    parent      = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subcategories",
        verbose_name="Categoría padre",
    )
    order       = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")
    is_active   = models.BooleanField(default=True, verbose_name="Activa")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        ordering = ['order', 'name']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def product_count(self):
        return self.products.filter(is_available=True).count()

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  SPEC ATTRIBUTE  (catálogo normalizado)
# ─────────────────────────────────────────────

class SpecAttribute(models.Model):
    name        = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    unit        = models.CharField(max_length=30, blank=True, verbose_name="Unidad")
    description = models.TextField(blank=True, verbose_name="Descripción")
    order       = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        db_table = 'spec_attributes'
        ordering = ['order', 'name']
        verbose_name = 'Atributo de especificación'
        verbose_name_plural = 'Atributos de especificación'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  PRODUCT
# ─────────────────────────────────────────────

class Product(models.Model):
    name           = models.CharField(max_length=255, verbose_name="Nombre")
    slug           = models.SlugField(max_length=280, unique=True, blank=True)
    description    = models.TextField(verbose_name="Descripción")
    price          = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio")
    original_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Precio original",
    )
    category       = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Categoría",
    )
    brand          = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Marca",
    )
    # Actualizado por señal post_save/post_delete en ProductStock
    total_stock    = models.IntegerField(default=0, verbose_name="Stock total", editable=False)
    is_available   = models.BooleanField(default=True, verbose_name="Disponible")
    is_featured    = models.BooleanField(default=False, verbose_name="Destacado")
    # Actualizado por señal post_save/post_delete en Review
    rating         = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="Calificación promedio")
    reviews_count  = models.PositiveIntegerField(default=0, verbose_name="N° reseñas")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round((1 - self.price / self.original_price) * 100)
        return 0

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  PRODUCT IMAGE
# ─────────────────────────────────────────────

class ProductImage(models.Model):
    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Producto",
    )
    image      = models.ImageField(upload_to='products/', verbose_name="Imagen")
    alt_text   = models.CharField(max_length=255, blank=True, verbose_name="Texto alternativo")
    is_primary = models.BooleanField(default=False, verbose_name="Imagen principal")
    order      = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        db_table = 'product_images'
        ordering = ['order']
        verbose_name = 'Imagen de producto'
        verbose_name_plural = 'Imágenes de producto'

    def __str__(self):
        return f"Imagen #{self.order} — {self.product.name}"

    def save(self, *args, **kwargs):
        # Si se marca como primaria, desmarcar las demás del mismo producto
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────
#  PRODUCT STOCK  (stock por punto físico)
# ─────────────────────────────────────────────

class ProductStock(models.Model):
    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_entries",
        verbose_name="Producto",
    )
    location   = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="stock_entries",
        verbose_name="Punto físico",
    )
    quantity   = models.IntegerField(default=0, verbose_name="Cantidad disponible")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_stock'
        verbose_name = 'Stock por ubicación'
        verbose_name_plural = 'Stock por ubicación'
        constraints = [
            models.UniqueConstraint(fields=["product", "location"], name="uniq_product_stock_location"),
        ]

    def __str__(self):
        return f"{self.product.name} | {self.location.name}: {self.quantity} uds"


# ─────────────────────────────────────────────
#  PRODUCT SPECIFICATION
# ─────────────────────────────────────────────

class ProductSpec(models.Model):
    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specifications",
        verbose_name="Producto",
    )
    attribute  = models.ForeignKey(
        SpecAttribute,
        on_delete=models.PROTECT,
        related_name="product_specs",
        verbose_name="Atributo",
    )
    value      = models.CharField(max_length=255, verbose_name="Valor")
    order      = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        db_table = 'product_specs'
        ordering = ['order']
        verbose_name = 'Especificación'
        verbose_name_plural = 'Especificaciones'
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute"], name="uniq_product_spec_attribute"),
        ]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


# ─────────────────────────────────────────────
#  REVIEW
# ─────────────────────────────────────────────

class Review(models.Model):
    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Producto",
    )
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Usuario",
    )
    rating     = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="Calificación (1-5)",
    )
    title      = models.CharField(max_length=200, blank=True, verbose_name="Título")
    comment    = models.TextField(blank=True, verbose_name="Comentario")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="uniq_review_product_user"),
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="chk_review_rating_range",
            ),
        ]

    def __str__(self):
        return f"Reseña → {self.product.name} ({self.rating}★)"


# ─────────────────────────────────────────────
#  ORDER
# ─────────────────────────────────────────────

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING   = "pending",   "Pendiente"
        PAID      = "paid",      "Pagado"
        PREPARING = "preparing", "En preparación"
        SHIPPING  = "shipping",  "En camino"
        DELIVERED = "delivered", "Entregado"
        INSTALLED = "installed", "Instalado"
        CANCELLED = "cancelled", "Cancelado"

    class PaymentMethod(models.TextChoices):
        WOMPI = "wompi",            "Wompi (tarjeta/PSE/Nequi)"
        CASH  = "cash",             "Contra entrega"

    # ── Identificadores ───────────────────────────────────────────────────────
    tracking_code = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True,
        verbose_name="Código de seguimiento (UUID)",
    )
    order_number  = models.CharField(
        max_length=20, unique=True, editable=False, default='',
        verbose_name="Número de orden (ORD-XXXXX)",
    )

    # ── Cliente ───────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
        verbose_name="Usuario registrado",
    )
    customer_name  = models.CharField(max_length=200, default='', verbose_name="Nombre del cliente")
    customer_email = models.EmailField(default='', verbose_name="Correo del cliente")
    customer_phone = models.CharField(max_length=30, blank=True, default='', verbose_name="Teléfono del cliente")

    # ── Envío ─────────────────────────────────────────────────────────────────
    shipping_address = models.TextField(default='', verbose_name="Dirección de envío")
    city             = models.CharField(max_length=100, blank=True, default='', verbose_name="Ciudad")
    department       = models.CharField(max_length=100, blank=True, verbose_name="Departamento")
    postal_code      = models.CharField(max_length=20, blank=True, verbose_name="Código postal")

    # ── Contabilidad ──────────────────────────────────────────────────────────
    subtotal      = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Subtotal")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo de envío")
    total         = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Total")

    # ── Pago ──────────────────────────────────────────────────────────────────
    payment_method       = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Método de pago",
    )
    wompi_transaction_id = models.CharField(
        max_length=200, blank=True,
        verbose_name="ID de transacción Wompi",
    )
    wompi_reference      = models.CharField(
        max_length=200, blank=True,
        verbose_name="Referencia Wompi",
    )

    # ── Estado ────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Estado",
    )
    notes = models.TextField(blank=True, verbose_name="Notas del pedido")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def save(self, *args, **kwargs):
        if not self.order_number:
            last = Order.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.order_number = f"ORD-{next_id:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} [{self.status}] — {self.customer_name}"


# ─────────────────────────────────────────────
#  ORDER ITEM
# ─────────────────────────────────────────────

class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Pedido")
    product    = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items", verbose_name="Producto")
    quantity   = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio unitario")

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Ítem de pedido'
        verbose_name_plural = 'Ítems de pedido'
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="uniq_order_item_product"),
            models.CheckConstraint(check=models.Q(quantity__gt=0), name="chk_order_item_quantity_positive"),
            models.CheckConstraint(check=models.Q(unit_price__gte=0), name="chk_order_item_price_nonneg"),
        ]

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


# ─────────────────────────────────────────────
#  TRACKING EVENT
# ─────────────────────────────────────────────

class TrackingEvent(models.Model):
    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tracking_history", verbose_name="Pedido")
    status      = models.CharField(max_length=15, choices=Order.Status.choices, verbose_name="Estado")
    description = models.TextField(verbose_name="Descripción del evento")
    location    = models.CharField(max_length=255, blank=True, verbose_name="Ubicación")
    timestamp   = models.DateTimeField(default=timezone.now, verbose_name="Fecha y hora")

    class Meta:
        db_table = 'tracking_events'
        ordering = ['timestamp']
        verbose_name = 'Evento de seguimiento'
        verbose_name_plural = 'Eventos de seguimiento'

    def __str__(self):
        return f"Pedido #{self.order_id} → {self.status}"


# ─────────────────────────────────────────────
#  SEÑALES — sincronizar rating y stock
# ─────────────────────────────────────────────

from django.db.models import Avg, Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


def _sync_product_rating(product_id):
    agg = Review.objects.filter(product_id=product_id).aggregate(avg=Avg("rating"))
    Product.objects.filter(pk=product_id).update(
        rating=round(agg["avg"] or 0, 2),
        reviews_count=Review.objects.filter(product_id=product_id).count(),
    )


@receiver(post_save, sender=Review)
def on_review_save(sender, instance, **kwargs):
    _sync_product_rating(instance.product_id)


@receiver(post_delete, sender=Review)
def on_review_delete(sender, instance, **kwargs):
    _sync_product_rating(instance.product_id)


def _sync_product_total_stock(product_id):
    agg = ProductStock.objects.filter(product_id=product_id).aggregate(total=Sum("quantity"))
    Product.objects.filter(pk=product_id).update(total_stock=agg["total"] or 0)


@receiver(post_save, sender=ProductStock)
def on_stock_save(sender, instance, **kwargs):
    _sync_product_total_stock(instance.product_id)


@receiver(post_delete, sender=ProductStock)
def on_stock_delete(sender, instance, **kwargs):
    _sync_product_total_stock(instance.product_id)
