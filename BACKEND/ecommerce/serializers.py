from rest_framework import serializers
from .models import (
    Brand, Location, Category, SpecAttribute,
    Product, ProductImage, ProductStock, ProductSpec,
    Review, Order, OrderItem, TrackingEvent,
    UserAddress, Favorite, Notification, FCMDeviceToken,
)


# ─── Auxiliares ───────────────────────────────────────────────────────────────

class BrandSerializer(serializers.ModelSerializer):

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'city', 'phone', 'hours_weekday', 'hours_saturday', 'hours_sunday', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'description', 'parent_id', 'order', 'is_active', 'product_count', 'created_at']
        read_only_fields = ['id', 'slug', 'product_count', 'created_at']


class SpecAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecAttribute
        fields = ['id', 'name', 'slug', 'unit', 'description', 'order']
        read_only_fields = ['id', 'slug']


# ─── Product sub-resources ────────────────────────────────────────────────────

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'product_id', 'image', 'image_url', 'alt_text', 'is_primary', 'order']
        read_only_fields = ['id', 'product_id', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ProductImageUploadSerializer(serializers.ModelSerializer):
    """Serializer para subir una imagen (multipart/form-data)."""

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_primary', 'order']

    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('La imagen no puede superar 5 MB.')
        if getattr(value, 'content_type', '').lower() not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise serializers.ValidationError('Formato no permitido. Usa JPEG, PNG o WebP.')
        return value


class ProductStockSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    location_city = serializers.CharField(source='location.city', read_only=True)

    class Meta:
        model = ProductStock
        fields = ['id', 'product_id', 'location_id', 'location_name', 'location_city', 'quantity', 'updated_at']
        read_only_fields = ['id', 'product_id', 'location_name', 'location_city', 'updated_at']


class ProductSpecSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)
    attribute_unit = serializers.CharField(source='attribute.unit', read_only=True)

    class Meta:
        model = ProductSpec
        fields = ['id', 'product_id', 'attribute_id', 'attribute_name', 'attribute_unit', 'value', 'order']
        read_only_fields = ['id', 'product_id', 'attribute_name', 'attribute_unit']


# ─── Product ──────────────────────────────────────────────────────────────────

class ProductListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name    = serializers.CharField(source='brand.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.ReadOnlyField()
    shipping_ready = serializers.ReadOnlyField()
    shipping_missing_fields = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'original_price', 'discount_percentage',
            'category_id', 'category_name', 'brand_id', 'brand_name',
            'total_stock', 'is_available', 'is_featured',
            'rating', 'reviews_count', 'primary_image', 'shipping_ready', 'shipping_missing_fields',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'total_stock', 'rating', 'reviews_count', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request or getattr(request.user, 'tipo_usuario', 0) == 0:
            data['total_stock'] = max(0, data['total_stock'])
        return data

    def get_primary_image(self, obj):
        request = self.context.get('request')
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer completo con imágenes, specs y stock."""
    category    = CategorySerializer(read_only=True)
    brand       = BrandSerializer(read_only=True)
    images      = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecSerializer(many=True, read_only=True)
    stock_entries  = ProductStockSerializer(many=True, read_only=True)
    discount_percentage = serializers.ReadOnlyField()
    shipping_ready = serializers.ReadOnlyField()
    from shipping.serializers import ProductShippingSerializer
    shipping_profile = ProductShippingSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original_price', 'discount_percentage',
            'category_id', 'category', 'brand_id', 'brand',
            'total_stock', 'is_available', 'is_featured',
            'rating', 'reviews_count',
            'images', 'specifications', 'stock_entries', 'shipping_profile', 'shipping_ready',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'total_stock', 'rating', 'reviews_count', 'created_at', 'updated_at']


    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request or getattr(request.user, 'tipo_usuario', 0) == 0:
            data['total_stock'] = max(0, data['total_stock'])
            data.pop('stock_entries', None)
        return data


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/editar productos (sin imágenes — se suben aparte)."""
    description = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    from shipping.serializers import ProductShippingSerializer
    shipping_profile = ProductShippingSerializer(required=False)

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('El precio debe ser mayor que cero.')
        return value

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'original_price',
            'category', 'brand', 'is_available', 'is_featured', 'shipping_profile',
        ]

    def validate(self, data):
        from django.conf import settings
        incoming = data.get('shipping_profile')
        profile = getattr(self.instance, 'shipping_profile', None) if self.instance else None
        available = data.get('is_available', getattr(self.instance, 'is_available', True))
        publishing = self.instance is None or (not self.instance.is_available and available)
        if available and (incoming is not None or (settings.TCC_SHIPPING_ENABLED and publishing)):
            values = {field: getattr(profile, field) for field in ('requires_shipping', 'weight_kg', 'height_cm', 'width_cm', 'length_cm', 'declared_value')} if profile else {'requires_shipping': True}
            values.update(incoming or {})
            automatic = values.get('declared_value_from_price', getattr(profile, 'declared_value_from_price', False))
            if automatic:
                values['declared_value'] = data.get('price', getattr(self.instance, 'price', None))
                if values['declared_value'] is not None and values['declared_value'] * 100 < values.get('packages_per_unit', getattr(profile, 'packages_per_unit', 1)):
                    raise serializers.ValidationError({'price': 'El precio debe cubrir al menos un centavo por paquete.'})
            if values.get('requires_shipping', True) and any(not values.get(field) for field in ('weight_kg', 'height_cm', 'width_cm', 'length_cm', 'declared_value')):
                raise serializers.ValidationError({'shipping_profile': 'Completa peso, dimensiones y valor declarado por paquete antes de publicar un producto físico.'})
        original = data.get('original_price', getattr(self.instance, 'original_price', None))
        price    = data.get('price', getattr(self.instance, 'price', None))
        if original is not None and price is not None and original < price:
            raise serializers.ValidationError(
                {"original_price": "El precio original debe ser mayor o igual al precio actual."}
            )
        return data

    def create(self, validated_data):
        from django.db import transaction
        from shipping.models import ProductShippingProfile
        shipping = validated_data.pop('shipping_profile', None)
        with transaction.atomic():
            product = super().create(validated_data)
            if shipping is not None:
                ProductShippingProfile.objects.create(product=product, **shipping)
        return product

    def update(self, instance, validated_data):
        from django.db import transaction
        from shipping.models import ProductShippingProfile
        shipping = validated_data.pop('shipping_profile', None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if shipping is not None:
                ProductShippingProfile.objects.update_or_create(product=instance, defaults=shipping)
        return instance


# ─── Review ───────────────────────────────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'product_id', 'user_id', 'user_name', 'is_owner', 'rating', 'title', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'product_id', 'user_id', 'user_name', 'is_owner', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        profile = getattr(obj.user, 'usuario_rel', None)
        return getattr(profile, 'nombre_completo', None) or getattr(obj.user, 'usuario', 'Usuario')

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and request.user.pk == obj.user_id)

    def validate_comment(self, value):
        comment = value.strip()
        if len(comment) < 3:
            raise serializers.ValidationError('El comentario debe tener al menos 3 caracteres.')
        if len(comment) > 2000:
            raise serializers.ValidationError('El comentario no puede superar 2000 caracteres.')
        return comment


# ─── Order ────────────────────────────────────────────────────────────────────

class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingEvent
        fields = ['id', 'order_id', 'status', 'description', 'location', 'timestamp']
        read_only_fields = ['id', 'order_id']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name  = serializers.CharField(source='product.name', read_only=True)
    subtotal      = serializers.ReadOnlyField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'order_id', 'product_id', 'product_name', 'quantity', 'unit_price', 'subtotal', 'primary_image']
        read_only_fields = ['id', 'order_id', 'product_name', 'subtotal', 'primary_image']

    def get_primary_image(self, obj):
        request = self.context.get('request')
        img = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None


class OrderSerializer(serializers.ModelSerializer):
    items            = OrderItemSerializer(many=True, read_only=True)
    tracking_history = TrackingEventSerializer(many=True, read_only=True)
    shipment = serializers.SerializerMethodField()

    def get_shipment(self, obj):
        from shipping.serializers import shipment_data
        request = self.context.get('request')
        admin = bool(request and getattr(request.user, 'tipo_usuario', 0) in (1, 4))
        return shipment_data(obj, admin=admin)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'tracking_code',
            'user_id',
            'customer_name', 'customer_email', 'customer_phone',
            'shipping_address', 'city', 'department', 'postal_code', 'delivery_address', 'delivery_details',
            'subtotal', 'shipping_cost', 'discounts', 'taxes', 'total', 'paid_total',
            'status', 'payment_method',
            'wompi_transaction_id', 'wompi_reference',
            'wompi_status',
            'notes',
            'items', 'tracking_history', 'shipment',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'tracking_code',
            'user_id', 'subtotal', 'shipping_cost', 'discounts', 'taxes', 'total', 'paid_total',
            'delivery_address', 'delivery_details',
            'created_at', 'updated_at',
        ]


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=999,
        error_messages={
            'min_value': 'La cantidad debe ser mayor o igual a 1.',
            'invalid': 'La cantidad debe ser un número entero.',
        },
    )


class OrderCreateSerializer(serializers.Serializer):
    shipping_quote_id = serializers.UUIDField(required=False, allow_null=True)
    address_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    tcc_city_code = serializers.CharField(required=False, allow_blank=True, max_length=8)
    complement = serializers.CharField(required=False, allow_blank=True, max_length=200)
    neighborhood = serializers.CharField(required=False, allow_blank=True, max_length=100)
    delivery_instructions = serializers.CharField(required=False, allow_blank=True, max_length=300)
    """Serializer para crear un pedido (usuario autenticado o invitado)."""
    # Cliente
    customer_name  = serializers.CharField(max_length=200)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    # Envío
    shipping_address = serializers.CharField()
    city             = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    department       = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    postal_code      = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')

    # Pago
    payment_method   = serializers.ChoiceField(choices=['wompi', 'cash'])
    wompi_reference  = serializers.CharField(required=False, allow_blank=True, default='')

    # Notas
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    # Productos
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Se requiere al menos un producto.")
        return items


# ─── User Address ─────────────────────────────────────────────────────────────

class UserAddressSerializer(serializers.ModelSerializer):
    def validate_phone(self, value):
        import re
        digits = re.sub(r'\D', '', value)
        if not re.fullmatch(r'[+0-9(). \-]+', value) or not 7 <= len(digits) <= 15:
            raise serializers.ValidationError('Escribe un número de teléfono válido, incluyendo indicativo si corresponde.')
        return value

    class Meta:
        model = UserAddress
        fields = [
            'id', 'label', 'recipient_name', 'phone', 'address',
            'city', 'department', 'postal_code', 'is_default', 'tcc_city_code', 'complement', 'neighborhood', 'delivery_instructions',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        from shipping.catalog import city
        code = data.get('tcc_city_code', getattr(self.instance, 'tcc_city_code', ''))
        if code:
            location = city(code)
            if not location or any(data.get(field, getattr(self.instance, field, '')) != location[field] for field in ('city', 'department')):
                raise serializers.ValidationError({'city': 'Selecciona una ciudad del departamento indicado.'})
        return data


# ─── Favorite ─────────────────────────────────────────────────────────────────

class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'created_at']
        read_only_fields = ['id', 'created_at']


class FavoriteCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()


# ─── Notification ─────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message', 'link',
            'is_read', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FCMDeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDeviceToken
        fields = ['id', 'token', 'platform', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_active', 'created_at', 'updated_at']
        extra_kwargs = {'token': {'validators': []}}

    def validate_token(self, value):
        token = value.strip()
        if len(token) < 20:
            raise serializers.ValidationError('El token FCM no es válido.')
        return token


class PushNotificationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=1000)
    data = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


