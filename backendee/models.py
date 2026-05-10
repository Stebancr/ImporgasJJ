"""
=============================================================
  MODELOS DJANGO — PostgreSQL  (3FN optimizado)
  Basados en la estructura del frontend (ProductsPage, ProductDetailPage)
=============================================================

Estructura:
   1. User           → Usuarios del sistema (admin, operador, cliente)
   2. Brand          → Marcas (Haceb, Samsung, LG, Fisher, Stanley…)
   3. Location       → Puntos físicos / bodegas
                        Cada ubicación tiene su propio stock del producto
   4. Category       → Categorías con soporte de subcategorías
   5. SpecAttribute  → Catálogo normalizado de atributos de spec
                        Evita que 'Capacidad' y 'capacidad' sean dos entradas distintas
   6. Product        → Producto principal
                        · discount es @property derivado de price / original_price
                          → no se almacena, nunca puede quedar desincronizado
                        · total_stock es suma de ProductStock.quantity (desnormalizado)
   7. ProductStock   → Stock de un producto en un punto físico  UNIQUE(product, location)
   8. ProductImage   → Imágenes (1-N) — constraint DB: solo 1 imagen primaria por producto
   9. ProductSpec    → Especificaciones: FK a SpecAttribute + valor
                        UNIQUE(product, attribute) → imposible duplicar la misma spec
  10. Review         → Reseñas y calificaciones
                        UNIQUE(product, user) → un usuario, una reseña por producto
  11. Order          → Pedidos
  12. OrderItem      → Líneas de pedido — guarda unit_price al momento de compra
  13. TrackingEvent  → Historial de cambios de estado del pedido
=============================================================
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# ─────────────────────────────────────────────
#  USER
# ─────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra):
        extra.setdefault("role", User.Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, name, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Usuario personalizado. Usa email como identificador principal.

    Columnas:
        id          BIGSERIAL PRIMARY KEY
        email       VARCHAR(254) UNIQUE NOT NULL
        name        VARCHAR(150) NOT NULL
        phone       VARCHAR(20)
        address     TEXT
        role        VARCHAR(10)  — admin | operator | client
        is_active   BOOLEAN
        is_staff    BOOLEAN
        created_at  TIMESTAMPTZ
        updated_at  TIMESTAMPTZ
    """

    class Role(models.TextChoices):
        ADMIN    = "admin",    "Administrador"
        OPERATOR = "operator", "Operador"
        CLIENT   = "client",   "Cliente"

    email      = models.EmailField(unique=True, verbose_name="Correo electrónico")
    name       = models.CharField(max_length=150, verbose_name="Nombre completo")
    phone      = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    address    = models.TextField(blank=True, verbose_name="Dirección")
    role       = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name="Rol",
    )
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects    = UserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.name} <{self.email}>"


# ─────────────────────────────────────────────
#  BRAND
# ─────────────────────────────────────────────

class Brand(models.Model):
    """
    Marcas de productos.

    Ejemplos del frontend: Haceb, Samsung, LG, Fisher, Stanley, Bosch,
                           Challenger, Coltgas

    Columnas:
        id          BIGSERIAL PRIMARY KEY
        name        VARCHAR(100) UNIQUE NOT NULL
        slug        VARCHAR(120) UNIQUE NOT NULL
        logo        VARCHAR(255)        — URL o path de imagen
        description TEXT
        is_active   BOOLEAN
        created_at  TIMESTAMPTZ
    """

    name        = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    logo        = models.URLField(blank=True, verbose_name="Logo (URL)")
    description = models.TextField(blank=True, verbose_name="Descripción")
    is_active   = models.BooleanField(default=True, verbose_name="Activa")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"

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
    """
    Punto físico donde se almacena y vende stock.

    El mismo producto puede tener stock diferente en cada Location.
    El stock por ubicación se gestiona desde ProductStock.

    Ejemplos:
        Sede Norte — Calle 80 #45-10, Bogotá
        Sede Sur   — Av. 68 #12-30, Bogotá
        Bodega Central — Carrera 30 #1-90, Medellín

    Columnas:
        id         BIGSERIAL PRIMARY KEY
        name       VARCHAR(150) UNIQUE NOT NULL
        address    TEXT NOT NULL
        city       VARCHAR(100) NOT NULL
        phone      VARCHAR(20)
        is_active  BOOLEAN
        created_at TIMESTAMPTZ
    """

    name       = models.CharField(max_length=150, unique=True, verbose_name="Nombre")
    address    = models.TextField(verbose_name="Dirección")
    city       = models.CharField(max_length=100, verbose_name="Ciudad")
    phone      = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    is_active  = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "locations"
        ordering = ["city", "name"]
        verbose_name = "Punto físico"
        verbose_name_plural = "Puntos físicos"

    def __str__(self):
        return f"{self.name} — {self.city}"


# ─────────────────────────────────────────────
#  CATEGORY
# ─────────────────────────────────────────────

class Category(models.Model):
    """
    Categorías de productos con soporte de subcategorías (árbol de profundidad libre).

    Ejemplos del frontend:
        calentadores → Calentadores de Agua a Gas
        aires        → Aires Acondicionados
        reguladores  → Reguladores de Gas
        herramientas → Herramientas e Instalación

    Columnas:
        id          BIGSERIAL PRIMARY KEY
        name        VARCHAR(100) NOT NULL
        slug        VARCHAR(120) UNIQUE NOT NULL
        icon        VARCHAR(100)              — nombre del ícono (lucide-react)
        description TEXT
        parent_id   BIGINT FK(categories)     — NULL = categoría raíz
        order       SMALLINT
        is_active   BOOLEAN
        created_at  TIMESTAMPTZ
    """

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
        db_table = "categories"
        ordering = ["order", "name"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

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
#  SPEC ATTRIBUTE  (catálogo normalizado de atributos)
# ─────────────────────────────────────────────

class SpecAttribute(models.Model):
    """
    Catálogo único de atributos técnicos.

    Problema que resuelve: sin esta tabla, 'Capacidad', 'capacidad' y
    'CAPACIDAD' serían tres registros distintos en product_specs.

    Con esta tabla cada atributo existe exactamente UNA vez. Los productos
    referencian el mismo registro via FK, garantizando consistencia.

    Atributos comunes del frontend (ProductDetailPage):
        Capacidad, Tipo de Gas, Encendido, Tipo de Tiro,
        Potencia, Dimensiones, Peso, Garantía

    Columnas:
        id           BIGSERIAL PRIMARY KEY
        name         VARCHAR(150) UNIQUE NOT NULL   — ej: 'Capacidad'
        slug         VARCHAR(160) UNIQUE NOT NULL   — ej: 'capacidad'
        unit         VARCHAR(30)                    — ej: 'Litros/min', 'kW', 'kg'
        description  TEXT
        order        SMALLINT                       — orden de presentación sugerido
    """

    name        = models.CharField(max_length=150, unique=True, verbose_name="Nombre del atributo")
    slug        = models.SlugField(max_length=160, unique=True, blank=True)
    unit        = models.CharField(max_length=30, blank=True, verbose_name="Unidad de medida")
    description = models.TextField(blank=True, verbose_name="Descripción")
    order       = models.PositiveSmallIntegerField(default=0, verbose_name="Orden sugerido")

    class Meta:
        db_table = "spec_attributes"
        ordering = ["order", "name"]
        verbose_name = "Atributo de especificación"
        verbose_name_plural = "Atributos de especificación"

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
    """
    Producto principal.

    Decisiones de normalización:
      · discount NO se almacena — es dato derivado de price / original_price.
        Se expone como @property para evitar que quede desincronizado si el precio cambia.
      · rating y reviews_count SÍ se almacenan (desnormalización controlada)
        para evitar un AVG/COUNT en cada listado. Se actualizan via señal Django.

    Campos mapeados del frontend:
        id            → id
        name          → name
        description   → description
        price         → price
        originalPrice → original_price
        category      → category_id (FK)
        brand         → brand_id (FK)
        rating        → rating  (desnormalizado, actualizado por señal)
        reviewsCount  → reviews_count (desnormalizado)
        stock         → stock
        isAvailable   → is_available
        isFeatured    → is_featured
        discount      → @property calculado

    Columnas:
        id             BIGSERIAL PRIMARY KEY
        name           VARCHAR(255) NOT NULL
        slug           VARCHAR(280) UNIQUE NOT NULL
        description    TEXT NOT NULL
        price          NUMERIC(12,2) > 0
        original_price NUMERIC(12,2) >= price   (nullable)
        category_id    BIGINT FK(categories)
        brand_id       BIGINT FK(brands)
        stock          INT >= 0
        is_available   BOOLEAN
        is_featured    BOOLEAN
        rating         NUMERIC(3,2)  [0.00 – 5.00]
        reviews_count  INT >= 0
        search_vector  TSVECTOR      — full-text (actualizado por trigger/señal)
        created_at     TIMESTAMPTZ
        updated_at     TIMESTAMPTZ
    """

    name           = models.CharField(max_length=255, verbose_name="Nombre")
    slug           = models.SlugField(max_length=280, unique=True, blank=True)
    description    = models.TextField(verbose_name="Descripción")
    price          = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio")
    original_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Precio original",
        help_text="Precio antes del descuento. Debe ser >= precio actual.",
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
    # total_stock es la suma de ProductStock.quantity para todas las ubicaciones.
    # Se actualiza via señal — no editar directamente.
    total_stock    = models.PositiveIntegerField(default=0, verbose_name="Stock total", editable=False)
    is_available   = models.BooleanField(default=True, verbose_name="Disponible",
                         help_text="Flag manual. Desactiva el producto globalmente independiente del stock.")
    is_featured    = models.BooleanField(default=False, verbose_name="Destacado")
    # Desnormalizado — actualizado por señal post_save/post_delete en Review
    rating         = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=0,
        verbose_name="Calificación promedio",
    )
    reviews_count  = models.PositiveIntegerField(default=0, verbose_name="N° reseñas")
    # Campo para búsqueda full-text con PostgreSQL
    search_vector  = SearchVectorField(null=True, blank=True, editable=False)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    # ── Propiedad derivada: nunca se desincroniza con price ──────────────────
    @property
    def discount(self) -> int:
        """Porcentaje de descuento calculado desde original_price y price."""
        if self.original_price and self.original_price > self.price:
            return round((1 - self.price / self.original_price) * 100)
        return 0

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        indexes = [
            # Consultas de listado por categoría/marca filtrando disponibles
            models.Index(fields=["category", "is_available"], name="idx_products_cat_avail"),
            models.Index(fields=["brand", "is_available"],    name="idx_products_brand_avail"),
            # Ordenamiento y filtros de precio / calificación
            models.Index(fields=["price"],                    name="idx_products_price"),
            models.Index(fields=["-rating"],                  name="idx_products_rating"),
            # Productos destacados (índice parcial — solo filas TRUE)
            models.Index(
                fields=["is_featured"],
                name="idx_products_featured",
                condition=models.Q(is_featured=True),
            ),
            # Full-text search con GIN
            GinIndex(fields=["search_vector"],                name="idx_products_fts"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gt=0),
                name="chk_product_price_positive",
            ),
            models.CheckConstraint(
                check=models.Q(total_stock__gte=0),
                name="chk_product_total_stock_nonneg",
            ),
            models.CheckConstraint(
                check=models.Q(rating__gte=0) & models.Q(rating__lte=5),
                name="chk_product_rating_range",
            ),
            # Cuando hay original_price debe ser mayor o igual al precio actual
            models.CheckConstraint(
                check=(
                    models.Q(original_price__isnull=True) |
                    models.Q(original_price__gte=models.F("price"))
                ),
                name="chk_product_original_price_gte_price",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  PRODUCT IMAGE
# ─────────────────────────────────────────────

class ProductImage(models.Model):
    """
    Imágenes de un producto (relación 1-N).

    El frontend muestra un array de URLs en product.images[].
    El constraint DB garantiza que solo puede haber UNA imagen primaria
    por producto (índice parcial UNIQUE WHERE is_primary = TRUE).

    Columnas:
        id         BIGSERIAL PRIMARY KEY
        product_id BIGINT FK(products)
        image      VARCHAR(500)     — URL o path
        alt_text   VARCHAR(255)
        is_primary BOOLEAN          — imagen principal para listados
        order      SMALLINT         — orden en el carrusel del detalle
    """

    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Producto",
    )
    image      = models.URLField(max_length=500, verbose_name="URL imagen")
    alt_text   = models.CharField(max_length=255, blank=True, verbose_name="Texto alternativo")
    is_primary = models.BooleanField(default=False, verbose_name="Imagen principal")
    order      = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        db_table = "product_images"
        ordering = ["order"]
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"
        constraints = [
            # Solo 1 imagen primaria por producto a nivel de base de datos
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="uniq_product_primary_image",
            ),
        ]

    def __str__(self):
        return f"Imagen #{self.order} — {self.product.name}"


# ─────────────────────────────────────────────
#  PRODUCT STOCK  (stock por punto físico)
# ─────────────────────────────────────────────

class ProductStock(models.Model):
    """
    Stock de un producto en un punto físico específico.

    Relación M-N entre Product y Location con cantidad como atributo.
    UNIQUE(product, location) → un solo registro por combinación.

    Ejemplos:
        Calentador 13L  | Sede Norte   | qty=3
        Calentador 13L  | Sede Sur     | qty=7
        Aire 12000 BTU  | Sede Norte   | qty=1

    Columnas:
        id          BIGSERIAL PRIMARY KEY
        product_id  BIGINT FK(products)
        location_id BIGINT FK(locations)
        quantity    INT >= 0
        updated_at  TIMESTAMPTZ
        UNIQUE(product_id, location_id)
    """

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
    quantity   = models.PositiveIntegerField(default=0, verbose_name="Cantidad disponible")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_stock"
        verbose_name = "Stock por ubicación"
        verbose_name_plural = "Stock por ubicación"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location"],
                name="uniq_product_stock_location",
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="chk_product_stock_qty_nonneg",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} | {self.location.name}: {self.quantity} uds"


# ─────────────────────────────────────────────
#  PRODUCT SPECIFICATION
# ─────────────────────────────────────────────

class ProductSpec(models.Model):
    """
    Especificaciones técnicas de un producto.

    Diseño normalizado:
        · El NOMBRE del atributo vive en SpecAttribute (tabla catálogo).
          → 'Capacidad' se guarda UNA sola vez, todos los productos con
            ese atributo apuntan al mismo registro.
        · El VALOR es específico por producto y se guarda aquí.

    Ejemplo para el Calentador 13L:
        attribute → SpecAttribute(name='Capacidad')   value='13 Litros/min'
        attribute → SpecAttribute(name='Potencia')    value='26 kW'
        attribute → SpecAttribute(name='Peso')        value='12 kg'

    Columnas:
        id           BIGSERIAL PRIMARY KEY
        product_id   BIGINT FK(products)
        attribute_id BIGINT FK(spec_attributes)
        value        VARCHAR(255)
        order        SMALLINT
        UNIQUE(product_id, attribute_id)   — imposible duplicar el mismo atributo en un producto
    """

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
        db_table = "product_specs"
        ordering = ["order"]
        verbose_name = "Especificación"
        verbose_name_plural = "Especificaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attribute"],
                name="uniq_product_spec_attribute",
            ),
        ]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


# ─────────────────────────────────────────────
#  REVIEW
# ─────────────────────────────────────────────

class Review(models.Model):
    """
    Reseña de un producto por un usuario.

    Alimenta Product.rating y Product.reviews_count.

    Columnas:
        id         BIGSERIAL PRIMARY KEY
        product    BIGINT FK(products)
        user       BIGINT FK(users)
        rating     SMALLINT (1-5)
        title      VARCHAR(200)
        comment    TEXT
        created_at TIMESTAMPTZ
        updated_at TIMESTAMPTZ
    """

    product    = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Producto",
    )
    user       = models.ForeignKey(
        User,
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
        db_table = "reviews"
        verbose_name = "Reseña"
        verbose_name_plural = "Reseñas"
        constraints = [
            # Un usuario, una sola reseña por producto
            models.UniqueConstraint(
                fields=["product", "user"],
                name="uniq_review_product_user",
            ),
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="chk_review_rating_range",
            ),
        ]

    def __str__(self):
        return f"{self.user.name} → {self.product.name} ({self.rating}★)"


# ─────────────────────────────────────────────
#  ORDER
# ─────────────────────────────────────────────

class Order(models.Model):
    """
    Pedido realizado por un usuario.

    Estados mapeados del frontend:
        pending   → Pendiente de pago
        paid      → Pagado
        preparing → En preparación
        shipping  → En camino
        delivered → Entregado
        installed → Instalado

    Columnas:
        id               BIGSERIAL PRIMARY KEY
        user             BIGINT FK(users)
        total            NUMERIC(14,2)
        status           VARCHAR(15)
        payment_method   VARCHAR(50)
        shipping_address TEXT
        created_at       TIMESTAMPTZ
        updated_at       TIMESTAMPTZ
    """

    class Status(models.TextChoices):
        PENDING   = "pending",   "Pendiente"
        PAID      = "paid",      "Pagado"
        PREPARING = "preparing", "En preparación"
        SHIPPING  = "shipping",  "En camino"
        DELIVERED = "delivered", "Entregado"
        INSTALLED = "installed", "Instalado"

    user             = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Cliente",
    )
    total            = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Total")
    status           = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Estado",
    )
    payment_method   = models.CharField(max_length=50, verbose_name="Método de pago")
    shipping_address = models.TextField(verbose_name="Dirección de envío")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        indexes = [
            models.Index(fields=["user",   "status"], name="idx_orders_user_status"),
            models.Index(fields=["status"],            name="idx_orders_status"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total__gte=0),
                name="chk_order_total_nonneg",
            ),
        ]

    def __str__(self):
        return f"Pedido #{self.id} — {self.user.name} [{self.status}]"


# ─────────────────────────────────────────────
#  ORDER ITEM
# ─────────────────────────────────────────────

class OrderItem(models.Model):
    """
    Línea de detalle de un pedido (CartItem en el frontend).

    Almacena unit_price al momento de la compra para preservar historial
    aunque el precio del producto cambie en el futuro.

    Columnas:
        id          BIGSERIAL PRIMARY KEY
        order       BIGINT FK(orders)
        product     BIGINT FK(products)
        quantity    INT
        unit_price  NUMERIC(12,2)   — precio al momento de compra
    """

    order      = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Pedido",
    )
    product    = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Producto",
    )
    quantity   = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio unitario")

    class Meta:
        db_table = "order_items"
        verbose_name = "Ítem de pedido"
        verbose_name_plural = "Ítems de pedido"
        constraints = [
            # No puede haber dos líneas con el mismo producto en el mismo pedido
            models.UniqueConstraint(
                fields=["order", "product"],
                name="uniq_order_item_product",
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="chk_order_item_quantity_positive",
            ),
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name="chk_order_item_price_nonneg",
            ),
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
    """
    Historial de cambios de estado de un pedido.

    Mapeado del frontend: Order.trackingHistory[]

    Columnas:
        id          BIGSERIAL PRIMARY KEY
        order       BIGINT FK(orders)
        status      VARCHAR(15)
        description TEXT
        location    VARCHAR(255)
        timestamp   TIMESTAMPTZ
    """

    order       = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tracking_history",
        verbose_name="Pedido",
    )
    status      = models.CharField(
        max_length=15,
        choices=Order.Status.choices,
        verbose_name="Estado",
    )
    description = models.TextField(verbose_name="Descripción del evento")
    location    = models.CharField(max_length=255, blank=True, verbose_name="Ubicación")
    timestamp   = models.DateTimeField(default=timezone.now, verbose_name="Fecha y hora")

    class Meta:
        db_table = "tracking_events"
        ordering = ["timestamp"]
        verbose_name = "Evento de seguimiento"
        verbose_name_plural = "Eventos de seguimiento"

    def __str__(self):
        return f"Pedido #{self.order_id} → {self.status} ({self.timestamp:%Y-%m-%d %H:%M})"


# ─────────────────────────────────────────────
#  SEÑALES — mantener rating/reviews_count sincronizados
# ─────────────────────────────────────────────

from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


def _sync_product_rating(product_id: int) -> None:
    """Recalcula y persiste rating y reviews_count en el producto."""
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


def _sync_product_total_stock(product_id: int) -> None:
    """Suma el stock de todas las ubicaciones y lo persiste en Product.total_stock."""
    from django.db.models import Sum
    agg = ProductStock.objects.filter(product_id=product_id).aggregate(total=Sum("quantity"))
    Product.objects.filter(pk=product_id).update(
        total_stock=agg["total"] or 0,
    )


@receiver(post_save, sender=ProductStock)
def on_stock_save(sender, instance, **kwargs):
    _sync_product_total_stock(instance.product_id)


@receiver(post_delete, sender=ProductStock)
def on_stock_delete(sender, instance, **kwargs):
    _sync_product_total_stock(instance.product_id)
