from rest_framework import serializers
from .models import (
    Brand, Location, Category, SpecAttribute,
    Product, ProductImage, ProductStock, ProductSpec,
    Review, Order, OrderItem, TrackingEvent,
    UserAddress, Favorite, Notification,
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

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'original_price', 'discount_percentage',
            'category_id', 'category_name', 'brand_id', 'brand_name',
            'total_stock', 'is_available', 'is_featured',
            'rating', 'reviews_count', 'primary_image',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'total_stock', 'rating', 'reviews_count', 'created_at', 'updated_at']

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

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original_price', 'discount_percentage',
            'category_id', 'category', 'brand_id', 'brand',
            'total_stock', 'is_available', 'is_featured',
            'rating', 'reviews_count',
            'images', 'specifications', 'stock_entries',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'total_stock', 'rating', 'reviews_count', 'created_at', 'updated_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/editar productos (sin imágenes — se suben aparte)."""

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'original_price',
            'category', 'brand', 'is_available', 'is_featured',
        ]

    def validate(self, data):
        original = data.get('original_price')
        price    = data.get('price')
        if original is not None and price is not None and original < price:
            raise serializers.ValidationError(
                {"original_price": "El precio original debe ser mayor o igual al precio actual."}
            )
        return data


# ─── Review ───────────────────────────────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'product_id', 'user_id', 'rating', 'title', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']


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

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'tracking_code',
            'user_id',
            'customer_name', 'customer_email', 'customer_phone',
            'shipping_address', 'city', 'department', 'postal_code',
            'subtotal', 'shipping_cost', 'total',
            'status', 'payment_method',
            'wompi_transaction_id', 'wompi_reference',
            'notes',
            'items', 'tracking_history',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'tracking_code',
            'user_id', 'subtotal', 'shipping_cost', 'total',
            'created_at', 'updated_at',
        ]


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity   = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
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
    class Meta:
        model = UserAddress
        fields = [
            'id', 'label', 'recipient_name', 'phone', 'address',
            'city', 'department', 'postal_code', 'is_default',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


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


