from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import IsAdminUser, IsNormalUserOrAdmin, IsAuthenticatedUser

from .models import (
    Brand, Location, Category, SpecAttribute,
    Product, ProductImage, ProductStock, ProductSpec,
    Review, Order, OrderItem, TrackingEvent,
)
from .serializers import (
    BrandSerializer, LocationSerializer, CategorySerializer, SpecAttributeSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductCreateSerializer,
    ProductImageSerializer, ProductImageUploadSerializer,
    ProductStockSerializer, ProductSpecSerializer,
    ReviewSerializer,
    OrderSerializer, OrderCreateSerializer, TrackingEventSerializer,
)


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

        return paginate(qs, request, ProductListSerializer)

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
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticatedUser()]

    def get(self, request, product_id):
        reviews = Review.objects.filter(product_id=product_id).order_by('-created_at')
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
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product, user=request.user)
            return Response({'data': serializer.data}, status=201)
        return Response(serializer.errors, status=400)


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

        return Response(
            {'data': OrderSerializer(order, context={'request': request}).data},
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


class WompiWebhookView(APIView):
    """
    Webhook de Wompi — recibe confirmaciones de pago y actualiza el estado
    de la orden. Verificar firma HMAC si se configura el secreto en .env.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # no session/token auth para webhooks

    def post(self, request):
        event = request.data.get('event')
        data  = request.data.get('data', {})

        if event != 'transaction.updated':
            return Response({'ok': True})

        transaction_data = data.get('transaction', {})
        reference        = transaction_data.get('reference', '')
        tx_status        = transaction_data.get('status', '')
        tx_id            = transaction_data.get('id', '')

        if not reference:
            return Response({'error': 'reference missing'}, status=400)

        try:
            order = Order.objects.get(wompi_reference=reference)
        except Order.DoesNotExist:
            # Puede ser un pedido que aún no se creó o referencia inválida
            return Response({'error': 'order not found'}, status=404)

        if tx_status == 'APPROVED' and order.status == Order.Status.PENDING:
            order.status             = Order.Status.PAID
            order.wompi_transaction_id = tx_id
            order.save()
            TrackingEvent.objects.create(
                order       = order,
                status      = Order.Status.PAID,
                description = f"Pago confirmado vía Wompi. Transacción: {tx_id}",
            )
        elif tx_status in ('DECLINED', 'ERROR', 'VOIDED'):
            order.status = Order.Status.CANCELLED
            order.save()
            TrackingEvent.objects.create(
                order       = order,
                status      = Order.Status.CANCELLED,
                description = f"Pago rechazado vía Wompi (estado: {tx_status}). Transacción: {tx_id}",
            )

        return Response({'ok': True})


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

