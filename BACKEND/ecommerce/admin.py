from django.contrib import admin
from .models import (
    Brand, Location, Category, SpecAttribute,
    Product, ProductImage, ProductStock, ProductSpec,
    Review, Order, OrderItem, TrackingEvent,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductStockInline(admin.TabularInline):
    model = ProductStock
    extra = 0


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    extra = 0


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'is_active']
    list_filter = ['is_active', 'city']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name']


@admin.register(SpecAttribute)
class SpecAttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'brand', 'price', 'total_stock', 'is_available', 'is_featured', 'rating']
    list_filter = ['is_available', 'is_featured', 'category', 'brand']
    search_fields = ['name', 'description']
    readonly_fields = ['total_stock', 'rating', 'reviews_count', 'created_at', 'updated_at']
    inlines = [ProductImageInline, ProductStockInline, ProductSpecInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total', 'status', 'payment_method', 'created_at']
    list_filter = ['status']
    inlines = [OrderItemInline, TrackingEventInline]
