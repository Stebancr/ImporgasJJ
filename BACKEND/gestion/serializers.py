from rest_framework import serializers
from ecommerce.models import Location, Product, ProductStock
from .models import Cotizacion, CotizacionItem, Factura, FacturaItem


# ─────────────────────────────────────────────
#  ITEM serializers
# ─────────────────────────────────────────────

class CotizacionItemInputSerializer(serializers.Serializer):
    producto_id     = serializers.IntegerField()
    descripcion     = serializers.CharField(max_length=255, required=False, allow_blank=True)
    cantidad        = serializers.IntegerField(min_value=1)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    descuento_item  = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class CotizacionItemSerializer(serializers.ModelSerializer):
    producto_id   = serializers.IntegerField(source='producto.id', read_only=True)
    producto_name = serializers.CharField(source='producto.name', read_only=True)

    class Meta:
        model = CotizacionItem
        fields = ['id', 'producto_id', 'producto_name', 'descripcion',
                  'cantidad', 'precio_unitario', 'descuento_item', 'subtotal']


class FacturaItemInputSerializer(serializers.Serializer):
    producto_id     = serializers.IntegerField()
    descripcion     = serializers.CharField(max_length=255, required=False, allow_blank=True)
    cantidad        = serializers.IntegerField(min_value=1)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    descuento_item  = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class FacturaItemSerializer(serializers.ModelSerializer):
    producto_id   = serializers.IntegerField(source='producto.id', read_only=True)
    producto_name = serializers.CharField(source='producto.name', read_only=True)

    class Meta:
        model = FacturaItem
        fields = ['id', 'producto_id', 'producto_name', 'descripcion',
                  'cantidad', 'precio_unitario', 'descuento_item', 'subtotal']


# ─────────────────────────────────────────────
#  COTIZACION
# ─────────────────────────────────────────────

class CotizacionListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    creado_por_usuario = serializers.CharField(source='creado_por.usuario', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero', 'location_name', 'creado_por_usuario',
            'cliente_nombre', 'cliente_cedula',
            'estado', 'fecha_emision', 'fecha_vencimiento',
            'subtotal', 'descuento_monto', 'impuesto_monto', 'total',
            'items_count', 'created_at',
        ]

    def get_items_count(self, obj):
        return obj.items.count()


class CotizacionDetailSerializer(serializers.ModelSerializer):
    location_id   = serializers.IntegerField(source='location.id', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    creado_por_usuario = serializers.CharField(source='creado_por.usuario', read_only=True)
    items = CotizacionItemSerializer(many=True, read_only=True)
    tiene_factura = serializers.SerializerMethodField()

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero',
            'location_id', 'location_name', 'creado_por_usuario',
            'cliente_nombre', 'cliente_cedula', 'cliente_correo', 'cliente_telefono',
            'estado', 'fecha_emision', 'fecha_vencimiento',
            'subtotal', 'descuento_pct', 'descuento_monto',
            'impuesto_pct', 'impuesto_monto', 'total',
            'notas', 'items', 'tiene_factura', 'created_at', 'updated_at',
        ]

    def get_tiene_factura(self, obj):
        return hasattr(obj, 'factura') and obj.factura is not None


class CotizacionCreateSerializer(serializers.Serializer):
    # location_id is resolved in the view (from user.location or explicit)
    location_id       = serializers.IntegerField(required=False)
    cliente_nombre    = serializers.CharField(max_length=200)
    cliente_cedula    = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    cliente_correo    = serializers.CharField(max_length=254, required=False, allow_blank=True, default='')
    cliente_telefono  = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    descuento_pct     = serializers.DecimalField(max_digits=5, decimal_places=2, default=0, min_value=0, max_value=100)
    impuesto_pct      = serializers.DecimalField(max_digits=5, decimal_places=2, default=0, min_value=0, max_value=100)
    notas             = serializers.CharField(required=False, allow_blank=True, default='')
    items             = CotizacionItemInputSerializer(many=True, min_length=1)


class CotizacionUpdateSerializer(serializers.Serializer):
    cliente_nombre    = serializers.CharField(max_length=200, required=False)
    cliente_cedula    = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cliente_correo    = serializers.CharField(max_length=254, required=False, allow_blank=True)
    cliente_telefono  = serializers.CharField(max_length=20, required=False, allow_blank=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    descuento_pct     = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100)
    impuesto_pct      = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100)
    estado            = serializers.ChoiceField(choices=[c[0] for c in Cotizacion.ESTADO_CHOICES], required=False)
    notas             = serializers.CharField(required=False, allow_blank=True)
    items             = CotizacionItemInputSerializer(many=True, required=False)


# ─────────────────────────────────────────────
#  FACTURA
# ─────────────────────────────────────────────

class FacturaListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    creado_por_usuario = serializers.CharField(source='creado_por.usuario', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Factura
        fields = [
            'id', 'numero', 'location_name', 'creado_por_usuario',
            'cliente_nombre', 'cliente_cedula',
            'estado', 'fecha_emision',
            'subtotal', 'descuento_monto', 'impuesto_monto', 'total',
            'items_count', 'created_at',
        ]

    def get_items_count(self, obj):
        return obj.items.count()


class FacturaDetailSerializer(serializers.ModelSerializer):
    location_id   = serializers.IntegerField(source='location.id', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    creado_por_usuario = serializers.CharField(source='creado_por.usuario', read_only=True)
    cotizacion_numero = serializers.SerializerMethodField()
    items = FacturaItemSerializer(many=True, read_only=True)

    class Meta:
        model = Factura
        fields = [
            'id', 'numero', 'cotizacion_numero',
            'location_id', 'location_name', 'creado_por_usuario',
            'cliente_nombre', 'cliente_cedula', 'cliente_correo', 'cliente_telefono',
            'estado', 'fecha_emision',
            'subtotal', 'descuento_pct', 'descuento_monto',
            'impuesto_pct', 'impuesto_monto', 'total',
            'notas', 'items', 'created_at', 'updated_at',
        ]

    def get_cotizacion_numero(self, obj):
        return obj.cotizacion.numero if obj.cotizacion else None


class FacturaCreateSerializer(serializers.Serializer):
    location_id       = serializers.IntegerField(required=False)
    cliente_nombre    = serializers.CharField(max_length=200)
    cliente_cedula    = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    cliente_correo    = serializers.CharField(max_length=254, required=False, allow_blank=True, default='')
    cliente_telefono  = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    descuento_pct     = serializers.DecimalField(max_digits=5, decimal_places=2, default=0, min_value=0, max_value=100)
    impuesto_pct      = serializers.DecimalField(max_digits=5, decimal_places=2, default=0, min_value=0, max_value=100)
    notas             = serializers.CharField(required=False, allow_blank=True, default='')
    items             = FacturaItemInputSerializer(many=True, min_length=1)


# ─────────────────────────────────────────────
#  STOCK (read-only, per location)
# ─────────────────────────────────────────────

class FacturaUpdateSerializer(serializers.Serializer):
    cliente_nombre   = serializers.CharField(max_length=200, required=False)
    cliente_cedula   = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cliente_correo   = serializers.CharField(max_length=254, required=False, allow_blank=True)
    cliente_telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    descuento_pct    = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100)
    impuesto_pct     = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100)
    notas            = serializers.CharField(required=False, allow_blank=True)
    items            = FacturaItemInputSerializer(many=True, min_length=1, required=False)


# ─────────────────────────────────────────────
#  STOCK (read-only, per location)
# ─────────────────────────────────────────────

class StockLocationSerializer(serializers.ModelSerializer):
    producto_id   = serializers.IntegerField(source='product.id', read_only=True)
    producto_name = serializers.CharField(source='product.name', read_only=True)
    producto_slug = serializers.CharField(source='product.slug', read_only=True)
    precio        = serializers.DecimalField(source='product.price', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductStock
        fields = ['id', 'producto_id', 'producto_name', 'producto_slug', 'precio', 'quantity', 'updated_at']
