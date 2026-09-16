from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import hashlib
import hmac
import logging
import requests

from usuarios.permissions import IsAdminUser, IsNormalUserOrAdmin, IsAuthenticatedUser

from .models import (
    Brand, Location, Category, SpecAttribute,
    Product, ProductImage, ProductStock, ProductSpec,
    Review, Order, OrderItem, TrackingEvent, WompiPaymentIntent,
    UserAddress, Favorite, Notification, FCMDeviceToken,
)
from .serializers import (
    BrandSerializer, LocationSerializer, CategorySerializer, SpecAttributeSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductCreateSerializer,
    ProductImageSerializer, ProductImageUploadSerializer,
    ProductStockSerializer, ProductSpecSerializer,
    ReviewSerializer,
    OrderSerializer, OrderCreateSerializer, TrackingEventSerializer,
    UserAddressSerializer, FavoriteSerializer, FavoriteCreateSerializer,
    NotificationSerializer, FCMDeviceTokenSerializer, PushNotificationSerializer,
)
from .firebase_service import send_push_to_user
from .email_service import send_order_payment_confirmation

logger = logging.getLogger(__name__)


# ─── helpers ──────────────────────────────────────────────────────────────────

def paginate(queryset, request, serializer_class, many=True):
    page     = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    offset   = (page - 1) * per_page
    total    = queryset.count()
    items    = queryset[offset: offset + per_page]
    data     = serializer_class(items, many=True, context={'request': request}).data
    return Response({
        'data':        data,
        'total':       total,
        'page':        page,
        'per_page':    per_page,
        'total_pages': max(1, -(-total // per_page)),
    })


# ─── Brand ────────────────────────────────────────────────────────────────────

class BrandListView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        qs = Brand.objects.all()
        if request.query_params.get('is_active'):
            qs = qs.filter(is_active=request.query_params['is_active'].lower() == 'true')
        if request.query_params.get('search'):
            qs = qs.filter(name__icontains=request.query_params['search'])
        return paginate(qs, request, BrandSerializer)

    def post(self, request):
        serializer = BrandSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BrandDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def _get(self, pk):
        try:
            return Brand.objects.get(pk=pk)
        except Brand.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': BrandSerializer(obj, context={'request': request}).data})

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = BrandSerializer(obj, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        # toggle-active shortcut
        if 'toggle' in request.path:
            obj.is_active = not obj.is_active
            obj.save()
            return Response({'data': BrandSerializer(obj, context={'request': request}).data})
        serializer = BrandSerializer(obj, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BrandToggleActiveView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            obj = Brand.objects.get(pk=pk)
        except Brand.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        obj.is_active = not obj.is_active
        obj.save()
        return Response({'data': BrandSerializer(obj, context={'request': request}).data})


# ─── Location ─────────────────────────────────────────────────────────────────

class LocationListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        qs = Location.objects.all()
        if request.query_params.get('is_active'):
            qs = qs.filter(is_active=request.query_params['is_active'].lower() == 'true')
        return paginate(qs, request, LocationSerializer)

    def post(self, request):
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data}, status=201)
        return Response(serializer.errors, status=400)


class LocationDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def _get(self, pk):
        try:
            return Location.objects.get(pk=pk)
        except Location.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': LocationSerializer(obj).data})

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = LocationSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = LocationSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=204)


class LocationToggleActiveView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            obj = Location.objects.get(pk=pk)
        except Location.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        obj.is_active = not obj.is_active
        obj.save()
        return Response({'data': LocationSerializer(obj).data})


# ─── Category ─────────────────────────────────────────────────────────────────

class CategoryListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        qs = Category.objects.all()
        if request.query_params.get('is_active'):
            qs = qs.filter(is_active=request.query_params['is_active'].lower() == 'true')
        if request.query_params.get('search'):
            qs = qs.filter(name__icontains=request.query_params['search'])
        return paginate(qs, request, CategorySerializer)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data}, status=201)
        return Response(serializer.errors, status=400)


class CategoryDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def _get(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': CategorySerializer(obj).data})

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = CategorySerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = CategorySerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=204)


class CategoryToggleActiveView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            obj = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        obj.is_active = not obj.is_active
        obj.save()
        return Response({'data': CategorySerializer(obj).data})


# ─── SpecAttribute ────────────────────────────────────────────────────────────

class SpecAttributeListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        qs = SpecAttribute.objects.all()
        return paginate(qs, request, SpecAttributeSerializer)

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        if name:
            existing = SpecAttribute.objects.filter(name__iexact=name).first()
            if existing:
                return Response({'data': SpecAttributeSerializer(existing).data}, status=200)
        serializer = SpecAttributeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data}, status=201)
        return Response(serializer.errors, status=400)


class SpecAttributeDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def _get(self, pk):
        try:
            return SpecAttribute.objects.get(pk=pk)
        except SpecAttribute.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': SpecAttributeSerializer(obj).data})

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = SpecAttributeSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=204)


# ─── Product ──────────────────────────────────────────────────────────────────

class ProductListView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        qs = Product.objects.select_related('category', 'brand').prefetch_related('images')

        # Filtros
        if request.query_params.get('category_id'):
            qs = qs.filter(category_id=request.query_params['category_id'])
        if request.query_params.get('brand_id'):
            qs = qs.filter(brand_id=request.query_params['brand_id'])
        if request.query_params.get('is_available'):
            val = request.query_params['is_available'].lower() == 'true'
            qs = qs.filter(is_available=val)
        if request.query_params.get('is_featured'):
            val = request.query_params['is_featured'].lower() == 'true'
            qs = qs.filter(is_featured=val)
        if request.query_params.get('min_price'):
            qs = qs.filter(price__gte=request.query_params['min_price'])
        if request.query_params.get('max_price'):
            qs = qs.filter(price__lte=request.query_params['max_price'])
        if request.query_params.get('search'):
            term = request.query_params['search']
            qs = qs.filter(
                Q(name__icontains=term) |
                Q(description__icontains=term) |
                Q(brand__name__icontains=term) |
                Q(category__name__icontains=term)
            )

        # Ordenamiento
        sort = request.query_params.get('sort', '')
        if sort == 'price-asc':
            qs = qs.order_by('price')
        elif sort == 'price-desc':
            qs = qs.order_by('-price')
        elif sort == 'rating':
            qs = qs.order_by('-rating', '-reviews_count')
        elif sort == 'newest':
            qs = qs.order_by('-created_at')
        else:
            qs = qs.order_by('-is_featured', '-created_at')

        # Metadata: categorías con conteo
        from django.db.models import Count
        categories_data = list(
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count('products', filter=Q(products__is_available=True)))
            .values('id', 'name', 'slug', 'product_count')
            .order_by('name')
        )

        # Metadata: marcas con conteo
        brands_data = list(
            Brand.objects.filter(is_active=True)
            .annotate(product_count=Count('products', filter=Q(products__is_available=True)))
            .values('id', 'name', 'slug', 'product_count')
            .order_by('name')
        )

        # Paginación
        page     = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        offset   = (page - 1) * per_page
        total    = qs.count()
        items    = qs[offset: offset + per_page]
        data     = ProductListSerializer(items, many=True, context={'request': request}).data

        return Response({
            'data':        data,
            'total':       total,
            'page':        page,
            'per_page':    per_page,
            'total_pages': max(1, -(-total // per_page)),
            'categories':  categories_data,
            'brands':      brands_data,
        })

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            # Procesar imágenes enviadas en el mismo request
            images = request.FILES.getlist('images')
            for idx, img_file in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=img_file,
                    alt_text=product.name,
                    is_primary=(idx == 0),
                    order=idx,
                )
            detail = ProductDetailSerializer(product, context={'request': request})
            return Response({'data': detail.data}, status=201)
        return Response(serializer.errors, status=400)


class ProductDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def _get(self, pk):
        try:
            return Product.objects.select_related('category', 'brand').prefetch_related(
                'images', 'specifications__attribute', 'stock_entries__location'
            ).get(pk=pk)
        except Product.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': ProductDetailSerializer(obj, context={'request': request}).data})

    def put(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = ProductCreateSerializer(obj, data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response({'data': ProductDetailSerializer(product, context={'request': request}).data})
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = ProductCreateSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            product = serializer.save()
            return Response({'data': ProductDetailSerializer(product, context={'request': request}).data})
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=204)


class ProductSlugView(APIView):
    """Obtener producto por slug (para el frontend de usuario)."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            product = Product.objects.select_related('category', 'brand').prefetch_related(
                'images', 'specifications__attribute', 'stock_entries__location'
            ).get(slug=slug, is_available=True)
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': ProductDetailSerializer(product, context={'request': request}).data})


# ─── Product Images ───────────────────────────────────────────────────────────

class ProductImageListView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request, product_id):
        images = ProductImage.objects.filter(product_id=product_id)
        return Response({'data': ProductImageSerializer(images, many=True, context={'request': request}).data})

    def post(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=404)

        serializer = ProductImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            image = serializer.save(product=product)
            return Response(
                {'data': ProductImageSerializer(image, context={'request': request}).data},
                status=201,
            )
        return Response(serializer.errors, status=400)


class ProductImageDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAdminUser]

    def _get(self, product_id, image_id):
        try:
            return ProductImage.objects.get(pk=image_id, product_id=product_id)
        except ProductImage.DoesNotExist:
            return None

    def patch(self, request, product_id, image_id):
        obj = self._get(product_id, image_id)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = ProductImageUploadSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': ProductImageSerializer(obj, context={'request': request}).data})
        return Response(serializer.errors, status=400)

    def delete(self, request, product_id, image_id):
        obj = self._get(product_id, image_id)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.image.delete(save=False)
        obj.delete()
        return Response(status=204)


# ─── Product Stock ────────────────────────────────────────────────────────────

class ProductStockListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request, product_id):
        entries = ProductStock.objects.filter(product_id=product_id).select_related('location')
        return Response({'data': ProductStockSerializer(entries, many=True).data})

    def post(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=404)
        location_id = request.data.get('location_id')
        quantity = request.data.get('quantity', 0)
        if not location_id:
            return Response({'error': 'location_id es requerido'}, status=400)
        obj, created = ProductStock.objects.get_or_create(
            product=product,
            location_id=location_id,
            defaults={'quantity': quantity},
        )
        if not created:
            obj.quantity = quantity
            obj.save()
        status_code = 201 if created else 200
        return Response({'data': ProductStockSerializer(obj).data}, status=status_code)


class ProductStockDetailView(APIView):
    permission_classes = [IsAdminUser]

    def _get(self, product_id, stock_id):
        try:
            return ProductStock.objects.get(pk=stock_id, product_id=product_id)
        except ProductStock.DoesNotExist:
            return None

    def put(self, request, product_id, stock_id):
        obj = self._get(product_id, stock_id)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = ProductStockSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, product_id, stock_id):
        obj = self._get(product_id, stock_id)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=204)


# ─── Product Specs ────────────────────────────────────────────────────────────

class ProductSpecListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request, product_id):
        specs = ProductSpec.objects.filter(product_id=product_id).select_related('attribute')
        return Response({'data': ProductSpecSerializer(specs, many=True).data})

    def post(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=404)
        attribute_id = request.data.get('attribute_id')
        if not attribute_id:
            return Response({'error': 'attribute_id es requerido'}, status=400)
        value = request.data.get('value', '')
        existing = ProductSpec.objects.filter(product=product, attribute_id=attribute_id).first()
        if existing:
            existing.value = value
            existing.save()
            return Response({'data': ProductSpecSerializer(existing).data})
        spec = ProductSpec.objects.create(
            product=product,
            attribute_id=attribute_id,
            value=value,
            order=request.data.get('order', 0),
        )
        return Response({'data': ProductSpecSerializer(spec).data}, status=201)


class ProductSpecDetailView(APIView):
    permission_classes = [IsAdminUser]

    def _get(self, product_id, spec_id):
        try:
            return ProductSpec.objects.get(pk=spec_id, product_id=product_id)
        except ProductSpec.DoesNotExist:
            return None

    def put(self, request, product_id, spec_id):
        obj = self._get(product_id, spec_id)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        serializer = ProductSpecSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, product_id, spec_id):
        obj = self._get(product_id, spec_id)
        if not obj:
            return Response({'error': 'Not found'}, status=404)
        obj.delete()
        return Response(status=204)


# ─── Reviews ──────────────────────────────────────────────────────────────────

class ProductReviewListView(APIView):
    throttle_scope = 'reviews'
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticatedUser()]

    def get(self, request, product_id):
        reviews = Review.objects.filter(product_id=product_id).select_related('user__usuario_rel').order_by('-created_at')
        return paginate(reviews, request, ReviewSerializer)

    def post(self, request, product_id):
        if not request.user.is_authenticated:
            return Response({'error': 'Autenticación requerida'}, status=401)
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=404)
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response({'error': 'Ya escribiste una reseña para este producto'}, status=400)
        serializer = ReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(product=product, user=request.user)
            return Response({'data': serializer.data}, status=201)
        return Response(serializer.errors, status=400)


class ProductReviewDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def _get_review(self, request, product_id, review_id):
        try:
            return Review.objects.get(pk=review_id, product_id=product_id, user=request.user)
        except Review.DoesNotExist:
            return None

    def patch(self, request, product_id, review_id):
        review = self._get_review(request, product_id, review_id)
        if not review:
            return Response({'error': 'Reseña no encontrada'}, status=404)
        serializer = ReviewSerializer(review, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, product_id, review_id):
        review = self._get_review(request, product_id, review_id)
        if not review:
            return Response({'error': 'Reseña no encontrada'}, status=404)
        review.delete()
        return Response(status=204)


# ─── Orders ───────────────────────────────────────────────────────────────────

SHIPPING_THRESHOLD = 500_000   # COP — envío gratis sobre este valor
SHIPPING_COST      = 25_000    # COP — costo de envío estándar


class OrderListView(APIView):
    """
    GET  → mis pedidos (usuario autenticado)
    POST → crear pedido (invitado o autenticado)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsNormalUserOrAdmin()]

    def get(self, request):
        qs = Order.objects.filter(user=request.user).prefetch_related(
            'items__product__images', 'tracking_history'
        )
        return paginate(qs, request, OrderSerializer)

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data       = serializer.validated_data
        items_data = data['items']
        if data['payment_method'] == 'wompi' and not settings.WOMPI_INTEGRITY_SECRET:
            return Response(
                {'error': 'La integración de pagos no está configurada.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # ── 1. Cargar productos y validar stock ───────────────────────────────
        products = {}
        errors   = []
        for item in items_data:
            pid = item['product_id']
            try:
                p = Product.objects.select_for_update().get(pk=pid, is_available=True)
            except Product.DoesNotExist:
                errors.append(f"Producto {pid} no disponible.")
                continue

            if p.total_stock < item['quantity']:
                errors.append(
                    f"Stock insuficiente para '{p.name}': "
                    f"disponible {p.total_stock}, solicitado {item['quantity']}."
                )
            products[pid] = p

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # ── 2. Calcular totales ───────────────────────────────────────────────
        subtotal = sum(
            products[item['product_id']].price * item['quantity']
            for item in items_data
        )
        shipping = 0 if subtotal >= SHIPPING_THRESHOLD else SHIPPING_COST
        total    = subtotal + shipping

        # Wompi recibe una intención de pago, no una orden. La orden y el
        # descuento de inventario ocurren únicamente tras la aprobación oficial.
        if data['payment_method'] == 'wompi':
            reference = data.get('wompi_reference', '')
            if not reference:
                return Response({'error': 'La referencia de pago es obligatoria.'}, status=400)
            intent, created = WompiPaymentIntent.objects.get_or_create(
                reference=reference,
                defaults={
                    'user': request.user if request.user.is_authenticated else None,
                    'checkout_data': {
                        'customer_name': data['customer_name'],
                        'customer_email': data['customer_email'],
                        'customer_phone': data.get('customer_phone', ''),
                        'shipping_address': data['shipping_address'],
                        'city': data.get('city', ''),
                        'department': data.get('department', ''),
                        'postal_code': data.get('postal_code', ''),
                        'notes': data.get('notes', ''),
                        'items': [{
                            'product_id': item['product_id'], 'quantity': item['quantity'],
                            'product_name': products[item['product_id']].name,
                            'unit_price': str(products[item['product_id']].price),
                        } for item in items_data],
                    },
                    'subtotal': subtotal, 'shipping_cost': shipping, 'total': total,
                },
            )
            existing_items = [(item['product_id'], item['quantity']) for item in intent.checkout_data.get('items', [])]
            submitted_items = [(item['product_id'], item['quantity']) for item in items_data]
            if not created and (intent.total != total or existing_items != submitted_items):
                return Response({'error': 'La referencia de pago ya fue utilizada.'}, status=409)
            amount_in_cents = int(intent.total * 100)
            signature_string = f"{intent.reference}{amount_in_cents}COP{settings.WOMPI_INTEGRITY_SECRET}"
            return Response({'data': {
                'tracking_code': str(intent.tracking_code),
                'wompi_reference': intent.reference,
                'wompi_public_key': settings.WOMPI_PUBLIC_KEY,
                'wompi_signature': hashlib.sha256(signature_string.encode()).hexdigest(),
                'total': str(intent.total),
                'payment_status': intent.wompi_status,
            }}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        # ── 3. Crear orden ────────────────────────────────────────────────────
        # El estado inicial depende del método de pago:
        #   wompi → PENDING (confirmar luego vía webhook)
        #   cash  → PAID (pago garantizado en entrega, pero lo marcamos PENDING hasta confirmar)
        order = Order.objects.create(
            user             = request.user if request.user.is_authenticated else None,
            customer_name    = data['customer_name'],
            customer_email   = data['customer_email'],
            customer_phone   = data.get('customer_phone', ''),
            shipping_address = data['shipping_address'],
            city             = data.get('city', ''),
            department       = data.get('department', ''),
            postal_code      = data.get('postal_code', ''),
            subtotal         = subtotal,
            shipping_cost    = shipping,
            total            = total,
            payment_method   = data['payment_method'],
            wompi_reference  = data.get('wompi_reference', ''),
            notes            = data.get('notes', ''),
            status           = Order.Status.PENDING,
            wompi_status     = Order.WompiStatus.PENDING if data['payment_method'] == 'wompi' else '',
        )

        # ── 4. Crear ítems y descontar stock ──────────────────────────────────
        for item in items_data:
            product = products[item['product_id']]
            qty     = item['quantity']

            OrderItem.objects.create(
                order      = order,
                product    = product,
                quantity   = qty,
                unit_price = product.price,
            )

            # Descontar del primer stock disponible (orden por cantidad desc)
            remaining = qty
            for stock_entry in ProductStock.objects.filter(
                product=product, quantity__gt=0
            ).order_by('-quantity').select_for_update():
                if remaining <= 0:
                    break
                deduct = min(stock_entry.quantity, remaining)
                stock_entry.quantity -= deduct
                stock_entry.save()
                remaining -= deduct

        # ── 5. Registrar primer evento de seguimiento ─────────────────────────
        TrackingEvent.objects.create(
            order       = order,
            status      = Order.Status.PENDING,
            description = (
                "Pedido recibido. Pendiente de confirmación de pago."
                if data['payment_method'] == 'wompi'
                else "Pedido recibido. Se cobrará contra entrega."
            ),
        )

        # ── 6. Generar signature para Wompi (si aplica) ───────────────────────
        wompi_signature = None
        if data['payment_method'] == 'wompi':
            amount_in_cents = int(total * 100)
            signature_string = f"{order.wompi_reference}{amount_in_cents}COP{settings.WOMPI_INTEGRITY_SECRET}"
            wompi_signature = hashlib.sha256(signature_string.encode()).hexdigest()

        # Construir respuesta
        response_data = OrderSerializer(order, context={'request': request}).data
        
        # Agregar signature a la respuesta si existe
        if wompi_signature:
            response_data['wompi_signature'] = wompi_signature

        return Response(
            {'data': response_data},
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    """GET → detalle de un pedido del usuario autenticado o por tracking_code."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            qs = Order.objects.prefetch_related('items__product__images', 'tracking_history')
            # Soporte para buscar por UUID de tracking (desde el frontend de seguimiento)
            try:
                import uuid as _uuid
                _uuid.UUID(str(pk))
                order = qs.get(tracking_code=pk)
            except (ValueError, AttributeError):
                order = qs.get(pk=pk)

            # Solo admin o el propietario pueden ver la orden por ID numérico
            if not str(pk).replace('-', '') == str(order.tracking_code).replace('-', ''):
                if not request.user.is_authenticated:
                    return Response({'error': 'Autenticación requerida'}, status=401)
                if order.user_id and order.user_id != request.user.id and not request.user.is_staff:
                    return Response({'error': 'No tienes permiso para ver este pedido'}, status=403)

        except Order.DoesNotExist:
            return Response({'error': 'Pedido no encontrado'}, status=404)

        return Response({'data': OrderSerializer(order, context={'request': request}).data})


class OrderByTrackingView(APIView):
    """GET público — consultar pedido por UUID de seguimiento."""
    permission_classes = [AllowAny]

    def get(self, request, tracking_code):
        try:
            order = Order.objects.prefetch_related(
                'items__product__images', 'tracking_history'
            ).get(tracking_code=tracking_code)
        except Order.DoesNotExist:
            return Response({'error': 'Pedido no encontrado'}, status=404)
        return Response({'data': OrderSerializer(order, context={'request': request}).data})


class OrderStatusPublicView(APIView):
    """
    GET público — busca un pedido por número de orden (ORD-XXXXX)
    o por código de seguimiento UUID.
    ?q=ORD-00001  or  ?q=<uuid>
    """
    permission_classes = [AllowAny]

    STATUS_LABELS = {
        'pending':   'Pendiente de pago',
        'paid':      'Pago confirmado',
        'preparing': 'En preparación',
        'shipping':  'En camino',
        'delivered': 'Entregado',
        'installed': 'Instalado',
        'cancelled': 'Cancelado',
    }

    def get(self, request):
        import uuid as uuid_lib
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'found': False, 'error': 'Ingresa el número de orden'}, status=400)

        order = Order.objects.filter(order_number__iexact=q).first()

        if not order:
            try:
                order = Order.objects.filter(tracking_code=uuid_lib.UUID(q)).first()
            except ValueError:
                pass

        if not order:
            return Response({'found': False})

        return Response({
            'found':         True,
            'order_number':  order.order_number,
            'tracking_code': str(order.tracking_code),
            'status':        order.status,
            'status_label':  self.STATUS_LABELS.get(order.status, order.status),
            'customer_name': order.customer_name,
            'total':         str(order.total),
            'created_at':    order.created_at.strftime('%d/%m/%Y'),
        })


def _wompi_property(data, path):
    value = data
    for part in path.split('.'):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def _valid_wompi_event(payload, header_checksum=''):
    signature = payload.get('signature') or {}
    properties = signature.get('properties') or []
    received = header_checksum or signature.get('checksum', '')
    timestamp = payload.get('timestamp')
    if not settings.WOMPI_EVENTS_SECRET or not properties or not received or timestamp is None:
        return False
    try:
        values = ''.join(str(_wompi_property(payload.get('data', {}), item)) for item in properties)
    except (KeyError, TypeError):
        return False
    expected = hashlib.sha256(f"{values}{timestamp}{settings.WOMPI_EVENTS_SECRET}".encode()).hexdigest()
    return hmac.compare_digest(expected.lower(), str(received).lower())


def _validate_wompi_intent(intent, transaction_data):
    try:
        amount_matches = int(transaction_data.get('amount_in_cents', -1)) == int(intent.total * 100)
    except (TypeError, ValueError):
        amount_matches = False
    return (
        transaction_data.get('reference') == intent.reference
        and transaction_data.get('currency') == intent.currency
        and amount_matches
        and transaction_data.get('status') in dict(Order.WompiStatus.choices)
        and bool(transaction_data.get('id'))
    )


def _create_approved_order(intent):
    """Materializa una intención aprobada una sola vez, bajo bloqueo de fila."""
    if intent.order_id:
        return intent.order
    data = intent.checkout_data
    order = Order.objects.create(
        user=intent.user, customer_name=data['customer_name'], customer_email=data['customer_email'],
        customer_phone=data.get('customer_phone', ''), shipping_address=data['shipping_address'],
        city=data.get('city', ''), department=data.get('department', ''),
        postal_code=data.get('postal_code', ''), notes=data.get('notes', ''),
        subtotal=intent.subtotal, shipping_cost=intent.shipping_cost, total=intent.total,
        payment_method=Order.PaymentMethod.WOMPI, wompi_reference=intent.reference,
        wompi_transaction_id=intent.transaction_id or '', wompi_status=Order.WompiStatus.APPROVED,
        status=Order.Status.PAID,
    )
    stock_shortages = []
    for item in data['items']:
        product = Product.objects.select_for_update().get(pk=item['product_id'])
        quantity = item['quantity']
        OrderItem.objects.create(
            order=order, product=product, quantity=quantity,
            unit_price=item.get('unit_price', product.price),
        )
        remaining = quantity
        for stock_entry in ProductStock.objects.filter(product=product, quantity__gt=0).order_by('-quantity').select_for_update():
            deduct = min(stock_entry.quantity, remaining)
            stock_entry.quantity -= deduct
            stock_entry.save()
            remaining -= deduct
            if remaining == 0:
                break
        if remaining:
            stock_shortages.append(f'{product.name}: {remaining} unidad(es)')
    description = 'Pago confirmado por Wompi. Orden creada.'
    if stock_shortages:
        description += ' Requiere gestión de inventario: ' + ', '.join(stock_shortages)
    TrackingEvent.objects.create(order=order, status=Order.Status.PAID, description=description)
    intent.order = order
    intent.processed_at = timezone.now()
    intent.save(update_fields=['order', 'processed_at', 'updated_at'])
    transaction.on_commit(lambda order_id=order.pk: send_order_payment_confirmation(order_id))
    return order


def _apply_wompi_intent_status(intent, transaction_data):
    tx_status = transaction_data['status']
    tx_id = transaction_data['id']
    if intent.transaction_id and intent.transaction_id != tx_id:
        raise ValueError('La intención ya está asociada a otra transacción.')
    # Un pago aprobado nunca retrocede por eventos tardíos o duplicados.
    if intent.wompi_status == Order.WompiStatus.APPROVED and tx_status != Order.WompiStatus.APPROVED:
        return intent.order
    intent.transaction_id = tx_id
    intent.wompi_status = tx_status
    intent.provider_payload = transaction_data
    if tx_status == Order.WompiStatus.APPROVED:
        intent.approved_at = intent.approved_at or timezone.now()
    intent.save(update_fields=['transaction_id', 'wompi_status', 'provider_payload', 'approved_at', 'updated_at'])
    return _create_approved_order(intent) if tx_status == Order.WompiStatus.APPROVED else None


class WompiWebhookView(APIView):
    throttle_scope = 'wompi_webhook'
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        if not _valid_wompi_event(request.data, request.headers.get('X-Event-Checksum', '')):
            return Response({'error': 'invalid event signature'}, status=401)
        if request.data.get('event') != 'transaction.updated':
            return Response({'ok': True})
        transaction_data = request.data.get('data', {}).get('transaction', {})
        try:
            intent = WompiPaymentIntent.objects.select_for_update().get(reference=transaction_data.get('reference', ''))
        except WompiPaymentIntent.DoesNotExist:
            return Response({'error': 'payment intent not found'}, status=404)
        if not _validate_wompi_intent(intent, transaction_data):
            return Response({'error': 'transaction does not match payment intent'}, status=400)
        try:
            _apply_wompi_intent_status(intent, transaction_data)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=409)
        return Response({'ok': True})


class WompiPaymentStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'payment_status'

    def get(self, request):
        tracking_code = request.query_params.get('tracking', '').strip()
        transaction_id = request.query_params.get('transaction_id', '').strip()
        if not tracking_code:
            return Response({'error': 'tracking is required'}, status=400)
        try:
            intent = WompiPaymentIntent.objects.select_related('order').get(tracking_code=tracking_code)
        except (WompiPaymentIntent.DoesNotExist, ValueError):
            return Response({'error': 'payment intent not found'}, status=404)

        if transaction_id:
            if not settings.WOMPI_PUBLIC_KEY:
                return Response({'error': 'payment verification is not configured'}, status=503)
            try:
                response = requests.get(
                    f"{settings.WOMPI_API_URL.rstrip('/')}/transactions/{transaction_id}",
                    headers={'Authorization': f'Bearer {settings.WOMPI_PUBLIC_KEY}'},
                    timeout=settings.WOMPI_HTTP_TIMEOUT,
                )
                response.raise_for_status()
                transaction_data = response.json().get('data', {})
            except (requests.RequestException, ValueError):
                logger.exception('No fue posible consultar la transacción Wompi %s', transaction_id)
                return Response({'error': 'payment provider unavailable'}, status=502)
            if not _validate_wompi_intent(intent, transaction_data):
                return Response({'error': 'transaction does not match payment intent'}, status=400)
            with transaction.atomic():
                intent = WompiPaymentIntent.objects.select_for_update().get(pk=intent.pk)
                try:
                    _apply_wompi_intent_status(intent, transaction_data)
                except ValueError as exc:
                    return Response({'error': str(exc)}, status=409)
        intent.refresh_from_db()
        order = intent.order

        return Response({
            'order_number': order.order_number if order else '',
            'tracking_code': str(order.tracking_code) if order else '',
            'payment_tracking_code': str(intent.tracking_code),
            'reference': intent.reference,
            'transaction_id': intent.transaction_id or '',
            'payment_status': intent.wompi_status,
            'amount': str(intent.total), 'currency': intent.currency,
            'customer_name': intent.checkout_data.get('customer_name', ''),
            'items': ([{'product_name': item.product.name, 'quantity': item.quantity, 'unit_price': str(item.unit_price)} for item in order.items.select_related('product')]
                      if order else intent.checkout_data.get('items', [])),
        })


class OrderAdminListView(APIView):
    """Vista para administradores — lista y gestiona todos los pedidos."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Order.objects.all().prefetch_related(
            'items__product__images', 'tracking_history'
        ).select_related('user')

        if request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'])
        if request.query_params.get('search'):
            term = request.query_params['search']
            qs = qs.filter(
                Q(order_number__icontains=term) |
                Q(customer_name__icontains=term) |
                Q(customer_email__icontains=term)
            )
        if request.query_params.get('payment_method'):
            qs = qs.filter(payment_method=request.query_params['payment_method'])
        if request.query_params.get('date_from'):
            qs = qs.filter(created_at__date__gte=request.query_params['date_from'])
        if request.query_params.get('date_to'):
            qs = qs.filter(created_at__date__lte=request.query_params['date_to'])

        return paginate(qs, request, OrderSerializer)

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        new_status = request.data.get('status')
        if new_status and new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save()
            TrackingEvent.objects.create(
                order       = order,
                status      = new_status,
                description = request.data.get('description', f'Estado actualizado a {new_status}'),
                location    = request.data.get('location', ''),
            )
        return Response({'data': OrderSerializer(order, context={'request': request}).data})

# --- User Addresses -----------------------------------------------------------

class UserAddressListView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        addresses = UserAddress.objects.filter(user=request.user)
        serializer = UserAddressSerializer(addresses, many=True)
        return Response({'data': serializer.data})

    def post(self, request):
        serializer = UserAddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAddressDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def _get(self, user, pk):
        try:
            return UserAddress.objects.get(pk=pk, user=user)
        except UserAddress.DoesNotExist:
            return None

    def get(self, request, pk):
        addr = self._get(request.user, pk)
        if not addr:
            return Response({'error': 'Not found'}, status=404)
        return Response({'data': UserAddressSerializer(addr).data})

    def put(self, request, pk):
        addr = self._get(request.user, pk)
        if not addr:
            return Response({'error': 'Not found'}, status=404)
        serializer = UserAddressSerializer(addr, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data})
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        addr = self._get(request.user, pk)
        if not addr:
            return Response({'error': 'Not found'}, status=404)
        addr.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Favorites ----------------------------------------------------------------

class FavoriteListView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related('product__brand', 'product__category').prefetch_related('product__images')
        serializer = FavoriteSerializer(favorites, many=True, context={'request': request})
        return Response({'data': serializer.data})

    def post(self, request):
        create_ser = FavoriteCreateSerializer(data=request.data)
        if not create_ser.is_valid():
            return Response(create_ser.errors, status=400)
        
        product_id = create_ser.validated_data['product_id']
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=404)
        
        fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
        if not created:
            return Response({'error': 'Ya existe en favoritos'}, status=400)
        
        return Response({'data': FavoriteSerializer(fav, context={'request': request}).data}, status=status.HTTP_201_CREATED)


class FavoriteDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def delete(self, request, pk):
        try:
            fav = Favorite.objects.get(pk=pk, user=request.user)
        except Favorite.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        fav.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteByProductView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def delete(self, request, product_id):
        try:
            fav = Favorite.objects.get(user=request.user, product_id=product_id)
        except Favorite.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        fav.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Notifications ------------------------------------------------------------

class NotificationListView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        unread_only = request.query_params.get('unread', '').lower() == 'true'
        if unread_only:
            notifications = notifications.filter(is_read=False)
        serializer = NotificationSerializer(notifications, many=True)
        return Response({'data': serializer.data})


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        
        if 'is_read' in request.data:
            notif.is_read = request.data['is_read']
            notif.save()
        
        return Response({'data': NotificationSerializer(notif).data})

    def delete(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        notif.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'Todas las notificaciones marcadas como leídas'})


class FCMDeviceTokenListView(APIView):
    permission_classes = [IsAuthenticatedUser]
    throttle_scope = 'fcm'

    def get(self, request):
        devices = FCMDeviceToken.objects.filter(user=request.user)
        return Response({'data': FCMDeviceTokenSerializer(devices, many=True).data})

    def post(self, request):
        serializer = FCMDeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device, created = FCMDeviceToken.objects.update_or_create(
            token=serializer.validated_data['token'],
            defaults={
                'user': request.user,
                'platform': serializer.validated_data.get('platform', FCMDeviceToken.Platform.UNKNOWN),
                'is_active': True,
                'last_error': '',
            },
        )
        return Response(
            {'data': FCMDeviceTokenSerializer(device).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        token = str(request.data.get('token', '')).strip()
        if not token:
            return Response({'token': ['Este campo es obligatorio.']}, status=400)
        updated = FCMDeviceToken.objects.filter(user=request.user, token=token).update(is_active=False)
        if not updated:
            return Response({'error': 'Token no encontrado.'}, status=404)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPushNotificationView(APIView):
    permission_classes = [IsAdminUser]
    throttle_scope = 'fcm'

    def post(self, request):
        serializer = PushNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=serializer.validated_data['user_id'])
        except user_model.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=404)
        try:
            result = send_push_to_user(
                user,
                serializer.validated_data['title'],
                serializer.validated_data['body'],
                serializer.validated_data.get('data'),
            )
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=503)
        return Response({'data': result})
