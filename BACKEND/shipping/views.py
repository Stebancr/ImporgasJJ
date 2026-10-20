from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from ecommerce.serializers import OrderItemInputSerializer
from .catalog import cities
from .services import quote_shipping, estimate_shipping, enqueue_shipment
from .serializers import quote_data, shipment_data
from .models import Shipment, ShipmentEvent
from .tcc import TCCError


class QuoteInput(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
    items = OrderItemInputSerializer(many=True, allow_empty=False)
    address_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    customer_name = serializers.CharField(required=False, max_length=200)
    customer_phone = serializers.CharField(required=False, max_length=30)
    customer_email = serializers.EmailField()
    shipping_address = serializers.CharField(required=False, max_length=500)
    city = serializers.CharField(required=False, max_length=100)
    department = serializers.CharField(required=False, max_length=100)
    postal_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    tcc_city_code = serializers.CharField(required=False, allow_blank=True, max_length=8)
    complement = serializers.CharField(required=False, allow_blank=True, max_length=200)
    neighborhood = serializers.CharField(required=False, allow_blank=True, max_length=100)
    delivery_instructions = serializers.CharField(required=False, allow_blank=True, max_length=300)


class ShippingConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from .rollout import enabled_for
        return Response({'enabled': enabled_for(request.user), 'carrier': 'TCC',
                         'requires_shipping_confirmation': settings.TCC_REQUIRE_CONFIRMED_SHIPPING,
                         'tracking_api_available': False, 'units': {'weight': 'kg', 'dimensions': 'cm'}})


class CityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(cities())


class QuoteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'shipping_quote'

    def post(self, request):
        from .rollout import enabled_for
        if not enabled_for(request.user):
            return Response({'error': 'El transporte TCC aún no está habilitado.'}, status=503)
        data = QuoteInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            quote = quote_shipping(request.user, data.validated_data['items'], data.validated_data)
        except TCCError as exc:
            return Response({'error': str(exc), 'code': exc.code}, status=503)
        return Response(quote_data(quote))


class EstimateInput(serializers.Serializer):
    items = OrderItemInputSerializer(many=True, allow_empty=False)
    tcc_city_code = serializers.CharField(max_length=8)
    force = serializers.BooleanField(required=False, default=False)


class EstimateView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'shipping_quote'

    def post(self, request):
        from .rollout import enabled_for
        if not enabled_for(request.user):
            return Response({'error': 'El transporte TCC aún no está habilitado.'}, status=503)
        data = EstimateInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            result = estimate_shipping(data.validated_data['items'], data.validated_data)
        except TCCError as exc:
            return Response({'error': str(exc), 'code': exc.code}, status=503)
        return Response(result)


class ShipmentActionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'shipping_admin'

    def post(self, request, order_id, action):
        if getattr(request.user, 'tipo_usuario', 0) not in (1, 4):
            return Response({'error': 'No autorizado'}, status=403)
        # No endpoint is invented for the deferred tracking/cancellation work.
        if action == 'sync':
            return Response({'error': 'TCC aún no ha suministrado el contrato de seguimiento por API. Usa el enlace oficial.'}, status=409)
        if action != 'retry':
            return Response({'error': 'Acción no disponible'}, status=404)
        with transaction.atomic():
            shipment = Shipment.objects.select_for_update().filter(order_id=order_id).first()
            if not shipment:
                return Response({'error': 'Envío no encontrado'}, status=404)
            if shipment.state != Shipment.State.ERROR:
                return Response({'error': 'Este envío no permite reintento. Una entrega incierta requiere confirmación de TCC.'}, status=409)
            if not settings.TCC_SHIPPING_ENABLED or not settings.TCC_DISPATCH_ENABLED:
                return Response({'error': 'La creación de despachos está deshabilitada.'}, status=409)
            shipment.state, shipment.next_attempt_at = Shipment.State.PENDING, timezone.now()
            shipment.save(update_fields=['state', 'next_attempt_at', 'updated_at'])
            ShipmentEvent.objects.create(shipment=shipment, event_key=f'manual-retry-{shipment.attempts}',
                state=shipment.state, actor=request.user, description='Reintento solicitado por un administrador autorizado.')
            transaction.on_commit(lambda: enqueue_shipment(shipment.pk))
        return Response({'state': shipment.state}, status=202)
