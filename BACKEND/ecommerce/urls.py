from django.urls import path
from . import views

urlpatterns = [
    # ── Brands ────────────────────────────────────────────────────────────────
    path('brands', views.BrandListView.as_view(), name='brand-list'),
    path('brands/<int:pk>', views.BrandDetailView.as_view(), name='brand-detail'),
    path('brands/<int:pk>/toggle-active', views.BrandToggleActiveView.as_view(), name='brand-toggle'),

    # ── Locations ─────────────────────────────────────────────────────────────
    path('locations', views.LocationListView.as_view(), name='location-list'),
    path('locations/<int:pk>', views.LocationDetailView.as_view(), name='location-detail'),
    path('locations/<int:pk>/toggle-active', views.LocationToggleActiveView.as_view(), name='location-toggle'),

    # ── Categories ────────────────────────────────────────────────────────────
    path('categories', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>', views.CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<int:pk>/toggle-active', views.CategoryToggleActiveView.as_view(), name='category-toggle'),

    # ── Spec Attributes ───────────────────────────────────────────────────────
    path('spec-attributes', views.SpecAttributeListView.as_view(), name='spec-attr-list'),
    path('spec-attributes/<int:pk>', views.SpecAttributeDetailView.as_view(), name='spec-attr-detail'),

    # ── Products ──────────────────────────────────────────────────────────────
    path('products', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/slug/<slug:slug>', views.ProductSlugView.as_view(), name='product-slug'),

    # ── Product sub-resources ─────────────────────────────────────────────────
    path('products/<int:product_id>/images', views.ProductImageListView.as_view(), name='product-image-list'),
    path('products/<int:product_id>/images/<int:image_id>', views.ProductImageDetailView.as_view(), name='product-image-detail'),

    path('products/<int:product_id>/stock', views.ProductStockListView.as_view(), name='product-stock-list'),
    path('products/<int:product_id>/stock/<int:stock_id>', views.ProductStockDetailView.as_view(), name='product-stock-detail'),

    path('products/<int:product_id>/specs', views.ProductSpecListView.as_view(), name='product-spec-list'),
    path('products/<int:product_id>/specs/<int:spec_id>', views.ProductSpecDetailView.as_view(), name='product-spec-detail'),

    path('products/<int:product_id>/reviews', views.ProductReviewListView.as_view(), name='product-review-list'),

    # ── Orders (usuario) ──────────────────────────────────────────────────────
    path('orders', views.OrderListView.as_view(), name='order-list'),
    path('orders/status', views.OrderStatusPublicView.as_view(), name='order-status-public'),
    path('orders/<int:pk>', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/tracking/<uuid:tracking_code>', views.OrderByTrackingView.as_view(), name='order-tracking'),

    # ── Orders (admin) ────────────────────────────────────────────────────────
    path('admin/orders', views.OrderAdminListView.as_view(), name='order-admin-list'),
    path('admin/orders/<int:pk>', views.OrderAdminListView.as_view(), name='order-admin-detail'),

    # ── Wompi webhook ─────────────────────────────────────────────────────────
    path('webhooks/wompi', views.WompiWebhookView.as_view(), name='wompi-webhook'),

    # ── User Addresses ────────────────────────────────────────────────────────
    path('user/addresses', views.UserAddressListView.as_view(), name='user-address-list'),
    path('user/addresses/<int:pk>', views.UserAddressDetailView.as_view(), name='user-address-detail'),

    # ── Favorites ─────────────────────────────────────────────────────────────
    path('user/favorites', views.FavoriteListView.as_view(), name='favorite-list'),
    path('user/favorites/<int:pk>', views.FavoriteDetailView.as_view(), name='favorite-detail'),
    path('user/favorites/product/<int:product_id>', views.FavoriteByProductView.as_view(), name='favorite-by-product'),

    # ── Notifications ─────────────────────────────────────────────────────────
    path('user/notifications', views.NotificationListView.as_view(), name='notification-list'),
    path('user/notifications/<int:pk>', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('user/notifications/mark-all-read', views.NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
]

