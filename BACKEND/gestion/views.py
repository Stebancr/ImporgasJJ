from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ecommerce.models import Location, Product, ProductStock
from usuarios.permissions import IsAdminUser, IsSuperUserOrAdmin
from .models import Cotizacion, CotizacionItem, Factura, FacturaItem
from .serializers import (
    CotizacionCreateSerializer, CotizacionUpdateSerializer,
    CotizacionListSerializer, CotizacionDetailSerializer,
    FacturaCreateSerializer, FacturaUpdateSerializer, FacturaListSerializer, FacturaDetailSerializer,
    StockLocationSerializer,
)


# ─── permission helpers ────────────────────────────────────────────────────────

def _get_tipo(user):
    return getattr(user, 'tipo_usuario', 0)


def _resolve_location(user, request_data):
    """
    Returns (location, error_response).
    - tipo_usuario=1 → uses user.location (immutable)
    - tipo_usuario=4 → reads location_id from request data
    """
    tipo = _get_tipo(user)
    if tipo == 1:
        if not user.location:
            return None, Response({'error': 'Su usuario no tiene una sede asignada.'}, status=403)
        return user.location, None
    if tipo == 4:
        location_id = request_data.get('location_id')
        if not location_id:
            return None, Response({'error': 'location_id es requerido para administradores globales.'}, status=400)
        try:
            return Location.objects.get(pk=location_id), None
        except Location.DoesNotExist:
            return None, Response({'error': 'Sede no encontrada.'}, status=404)
    return None, Response({'error': 'Sin permiso.'}, status=403)


def _filter_by_location(user, queryset):
    """Restrict queryset to user's location if tipo_usuario=1."""
    tipo = _get_tipo(user)
    if tipo == 1:
        if not user.location:
            return queryset.none()
        return queryset.filter(location=user.location)
    if tipo == 4:
        return queryset
    return queryset.none()


def paginate_qs(queryset, request, serializer_class):
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    offset = (page - 1) * per_page
    total = queryset.count()
    items = queryset[offset: offset + per_page]
    data = serializer_class(items, many=True).data
    return Response({
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, -(-total // per_page)),
    })


# ─── Helpers for item creation ─────────────────────────────────────────────────

def _create_cotizacion_items(cotizacion, items_data):
    for item in items_data:
        product = Product.objects.get(pk=item['producto_id'])
        CotizacionItem.objects.create(
            cotizacion=cotizacion,
            producto=product,
            descripcion=item.get('descripcion') or product.name,
            cantidad=item['cantidad'],
            precio_unitario=item['precio_unitario'],
            descuento_item=item.get('descuento_item', 0),
        )
    cotizacion.recalcular_totales()


def _create_factura_items_and_deduct(factura, items_data, location):
    """Creates invoice items and decrements per-location stock atomically.
    Allows stock to go negative if insufficient — never blocks factura creation."""
    for item in items_data:
        product = Product.objects.select_for_update().get(pk=item['producto_id'])
        stock_entry, _ = ProductStock.objects.select_for_update().get_or_create(
            product=product, location=location,
            defaults={'quantity': 0}
        )
        FacturaItem.objects.create(
            factura=factura,
            producto=product,
            descripcion=item.get('descripcion') or product.name,
            cantidad=item['cantidad'],
            precio_unitario=item['precio_unitario'],
            descuento_item=item.get('descuento_item', 0),
        )
        # Decrement location stock; allow negative values
        ProductStock.objects.filter(pk=stock_entry.pk).update(quantity=F('quantity') - item['cantidad'])

    # Refresh total_stock on all affected products
    product_ids = [i['producto_id'] for i in items_data]
    for pid in set(product_ids):
        total = ProductStock.objects.filter(product_id=pid).aggregate(t=Sum('quantity'))['t'] or 0
        Product.objects.filter(pk=pid).update(total_stock=total)

    factura.recalcular_totales()


def _restore_factura_stock(factura):
    """Restores stock when an invoice is cancelled."""
    for item in factura.items.select_related('producto').all():
        ProductStock.objects.filter(
            product=item.producto, location=factura.location
        ).update(quantity=F('quantity') + item.cantidad)
        total = ProductStock.objects.filter(product=item.producto).aggregate(t=Sum('quantity'))['t'] or 0
        Product.objects.filter(pk=item.producto_id).update(total_stock=total)


# ─── Mi sede ──────────────────────────────────────────────────────────────────

class MiSedeView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    def get(self, request):
        user = request.user
        tipo = _get_tipo(user)
        location = getattr(user, 'location', None)
        return Response({
            'tipo_usuario': tipo,
            'location': {
                'id': location.id,
                'name': location.name,
                'address': location.address,
                'city': location.city,
            } if location else None,
        })


# ─── Asignar sede (super admin only) ─────────────────────────────────────────

class AsignarSedeView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        if _get_tipo(request.user) != 4:
            return Response({'error': 'Solo el super administrador puede asignar sedes.'}, status=403)
        usuario_id = request.data.get('usuario_id')
        location_id = request.data.get('location_id')
        if not usuario_id:
            return Response({'error': 'usuario_id requerido.'}, status=400)
        from usuarios.models import Credenciales
        try:
            cred = Credenciales.objects.get(pk=usuario_id)
        except Credenciales.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=404)
        if location_id:
            try:
                location = Location.objects.get(pk=location_id)
            except Location.DoesNotExist:
                return Response({'error': 'Sede no encontrada.'}, status=404)
            cred.location = location
        else:
            cred.location = None
        cred.save(update_fields=['location'])
        return Response({
            'message': 'Sede actualizada.',
            'usuario_id': cred.pk,
            'location_id': cred.location_id,
        })


# ─── STOCK por sede ───────────────────────────────────────────────────────────

class StockSedeView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    def get(self, request):
        user = request.user
        tipo = _get_tipo(user)

        location_id = request.query_params.get('location_id')
        if tipo == 1:
            if not user.location:
                return Response({'error': 'Sin sede asignada.'}, status=403)
            location_id = user.location_id

        search = request.query_params.get('search', '')

        # Super admin with no location filter → aggregate stock via Product.total_stock
        if tipo == 4 and not location_id:
            qs = Product.objects.filter(is_available=True).order_by('name')
            if search:
                qs = qs.filter(name__icontains=search)
            page     = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))
            offset   = (page - 1) * per_page
            total    = qs.count()
            products = list(qs[offset:offset + per_page])
            data = [
                {
                    'id':            p.id,
                    'producto_id':   p.id,
                    'producto_name': p.name,
                    'producto_slug': p.slug,
                    'precio':        str(p.price),
                    'quantity':      p.total_stock,
                    'updated_at':    p.updated_at.isoformat(),
                }
                for p in products
            ]
            return Response({
                'data':        data,
                'total':       total,
                'page':        page,
                'per_page':    per_page,
                'total_pages': max(1, -(-total // per_page)),
            })

        qs = ProductStock.objects.filter(
            location_id=location_id
        ).select_related('product').order_by('product__name')

        if search:
            qs = qs.filter(product__name__icontains=search)

        return paginate_qs(qs, request, StockLocationSerializer)

    def patch(self, request, product_id):
        """Update stock quantity for a product at the user's (or specified) location."""
        user = request.user
        tipo = _get_tipo(user)

        location_id = request.data.get('location_id') if tipo == 4 else (
            user.location_id if user.location else None
        )
        if not location_id:
            return Response({'error': 'Sin sede asignada o location_id no especificado.'}, status=400)

        quantity = request.data.get('quantity')
        if quantity is None or int(quantity) < 0:
            return Response({'error': 'quantity debe ser un entero >= 0.'}, status=400)

        try:
            stock_entry = ProductStock.objects.get(product_id=product_id, location_id=location_id)
        except ProductStock.DoesNotExist:
            return Response({'error': 'Entrada de stock no encontrada.'}, status=404)

        stock_entry.quantity = int(quantity)
        stock_entry.save(update_fields=['quantity'])

        # Update total_stock on product
        total = ProductStock.objects.filter(product_id=product_id).aggregate(t=Sum('quantity'))['t'] or 0
        Product.objects.filter(pk=product_id).update(total_stock=total)

        return Response(StockLocationSerializer(stock_entry).data)


# ─── COTIZACIONES ─────────────────────────────────────────────────────────────

class CotizacionListView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    def get(self, request):
        user = request.user
        tipo = _get_tipo(user)

        qs = Cotizacion.objects.select_related('location', 'creado_por').prefetch_related('items')
        qs = _filter_by_location(user, qs)

        if estado := request.query_params.get('estado'):
            qs = qs.filter(estado=estado)
        if location_id := request.query_params.get('location_id'):
            if tipo == 4:
                qs = qs.filter(location_id=location_id)
        if search := request.query_params.get('search'):
            qs = qs.filter(
                cliente_nombre__icontains=search
            ) | qs.filter(numero__icontains=search) | qs.filter(cliente_cedula__icontains=search)

        return paginate_qs(qs.distinct(), request, CotizacionListSerializer)

    @transaction.atomic
    def post(self, request):
        user = request.user
        tipo = _get_tipo(user)

        serializer = CotizacionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        location, err = _resolve_location(user, data)
        if err:
            return err

        try:
            cotizacion = Cotizacion.objects.create(
                location=location,
                creado_por=user,
                cliente_nombre=data['cliente_nombre'],
                cliente_cedula=data.get('cliente_cedula', ''),
                cliente_correo=data.get('cliente_correo', ''),
                cliente_telefono=data.get('cliente_telefono', ''),
                fecha_vencimiento=data.get('fecha_vencimiento'),
                descuento_pct=data.get('descuento_pct', 0),
                impuesto_pct=data.get('impuesto_pct', 0),
                notas=data.get('notas', ''),
            )
            _create_cotizacion_items(cotizacion, data['items'])
        except Product.DoesNotExist as e:
            return Response({'error': str(e)}, status=404)

        cotizacion.refresh_from_db()
        return Response({'data': CotizacionDetailSerializer(cotizacion).data}, status=201)


class CotizacionDetailView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    def _get_cotizacion(self, pk, user):
        try:
            cot = Cotizacion.objects.select_related('location', 'creado_por').prefetch_related('items__producto').get(pk=pk)
        except Cotizacion.DoesNotExist:
            return None, Response({'error': 'Cotización no encontrada.'}, status=404)
        tipo = _get_tipo(user)
        if tipo == 1 and user.location and cot.location_id != user.location_id:
            return None, Response({'error': 'Sin permiso para esta cotización.'}, status=403)
        if tipo not in [1, 4]:
            return None, Response({'error': 'Sin permiso.'}, status=403)
        return cot, None

    def get(self, request, pk):
        cot, err = self._get_cotizacion(pk, request.user)
        if err:
            return err
        return Response({'data': CotizacionDetailSerializer(cot).data})

    @transaction.atomic
    def put(self, request, pk):
        cot, err = self._get_cotizacion(pk, request.user)
        if err:
            return err
        if cot.estado not in ('borrador', 'enviada'):
            return Response({'error': 'Solo se pueden editar cotizaciones en estado borrador o enviada.'}, status=400)

        serializer = CotizacionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        updatable = ['cliente_nombre', 'cliente_cedula', 'cliente_correo', 'cliente_telefono',
                     'fecha_vencimiento', 'descuento_pct', 'impuesto_pct', 'estado', 'notas']
        for field in updatable:
            if field in data:
                setattr(cot, field, data[field])
        cot.save()

        if 'items' in data:
            cot.items.all().delete()
            try:
                _create_cotizacion_items(cot, data['items'])
            except Product.DoesNotExist as e:
                return Response({'error': str(e)}, status=404)
        else:
            cot.recalcular_totales()

        cot.refresh_from_db()
        return Response({'data': CotizacionDetailSerializer(cot).data})

    def delete(self, request, pk):
        cot, err = self._get_cotizacion(pk, request.user)
        if err:
            return err
        if cot.estado != 'borrador':
            return Response({'error': 'Solo se pueden eliminar cotizaciones en estado borrador.'}, status=400)
        cot.delete()
        return Response(status=204)


class CotizacionConvertirView(APIView):
    """Convert an approved quotation into an invoice, deducting stock."""
    permission_classes = [IsSuperUserOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        user = request.user
        tipo = _get_tipo(user)

        try:
            cot = Cotizacion.objects.select_related('location').prefetch_related('items__producto').get(pk=pk)
        except Cotizacion.DoesNotExist:
            return Response({'error': 'Cotización no encontrada.'}, status=404)

        if tipo == 1 and user.location and cot.location_id != user.location_id:
            return Response({'error': 'Sin permiso para esta cotización.'}, status=403)

        if hasattr(cot, 'factura') and cot.factura:
            return Response({'error': 'Esta cotización ya fue convertida en factura.'}, status=400)

        if cot.estado in ('rechazada', 'anulada', 'convertida'):
            return Response({'error': f'No se puede convertir una cotización en estado "{cot.estado}".'}, status=400)

        # Build items data from cotizacion items
        items_data = [
            {
                'producto_id': item.producto_id,
                'descripcion': item.descripcion,
                'cantidad': item.cantidad,
                'precio_unitario': item.precio_unitario,
                'descuento_item': item.descuento_item,
            }
            for item in cot.items.all()
        ]

        try:
            factura = Factura.objects.create(
                cotizacion=cot,
                location=cot.location,
                creado_por=user,
                cliente_nombre=cot.cliente_nombre,
                cliente_cedula=cot.cliente_cedula,
                cliente_correo=cot.cliente_correo,
                cliente_telefono=cot.cliente_telefono,
                descuento_pct=cot.descuento_pct,
                impuesto_pct=cot.impuesto_pct,
                notas=cot.notas,
            )
            _create_factura_items_and_deduct(factura, items_data, cot.location)
        except Product.DoesNotExist as e:
            return Response({'error': str(e)}, status=400)

        # Mark quotation as converted
        Cotizacion.objects.filter(pk=cot.pk).update(estado='convertida')

        factura.refresh_from_db()
        return Response({'data': FacturaDetailSerializer(factura).data}, status=201)


# ─── FACTURAS ─────────────────────────────────────────────────────────────────

class FacturaListView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    def get(self, request):
        user = request.user
        tipo = _get_tipo(user)

        qs = Factura.objects.select_related('location', 'creado_por').prefetch_related('items')
        qs = _filter_by_location(user, qs)

        if estado := request.query_params.get('estado'):
            qs = qs.filter(estado=estado)
        if location_id := request.query_params.get('location_id'):
            if tipo == 4:
                qs = qs.filter(location_id=location_id)
        if search := request.query_params.get('search'):
            qs = qs.filter(
                cliente_nombre__icontains=search
            ) | qs.filter(numero__icontains=search) | qs.filter(cliente_cedula__icontains=search)

        return paginate_qs(qs.distinct(), request, FacturaListSerializer)

    @transaction.atomic
    def post(self, request):
        user = request.user
        tipo = _get_tipo(user)

        serializer = FacturaCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        location, err = _resolve_location(user, data)
        if err:
            return err

        try:
            factura = Factura.objects.create(
                location=location,
                creado_por=user,
                cliente_nombre=data['cliente_nombre'],
                cliente_cedula=data.get('cliente_cedula', ''),
                cliente_correo=data.get('cliente_correo', ''),
                cliente_telefono=data.get('cliente_telefono', ''),
                descuento_pct=data.get('descuento_pct', 0),
                impuesto_pct=data.get('impuesto_pct', 0),
                notas=data.get('notas', ''),
            )
            _create_factura_items_and_deduct(factura, data['items'], location)
        except Product.DoesNotExist as e:
            return Response({'error': str(e)}, status=400)

        factura.refresh_from_db()
        return Response({'data': FacturaDetailSerializer(factura).data}, status=201)


class FacturaDetailView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    def _get_factura(self, pk, user):
        try:
            fac = Factura.objects.select_related('location', 'creado_por', 'cotizacion').prefetch_related('items__producto').get(pk=pk)
        except Factura.DoesNotExist:
            return None, Response({'error': 'Factura no encontrada.'}, status=404)
        tipo = _get_tipo(user)
        if tipo == 1 and user.location and fac.location_id != user.location_id:
            return None, Response({'error': 'Sin permiso para esta factura.'}, status=403)
        if tipo not in [1, 4]:
            return None, Response({'error': 'Sin permiso.'}, status=403)
        return fac, None

    def get(self, request, pk):
        fac, err = self._get_factura(pk, request.user)
        if err:
            return err
        return Response({'data': FacturaDetailSerializer(fac).data})

    @transaction.atomic
    def put(self, request, pk):
        fac, err = self._get_factura(pk, request.user)
        if err:
            return err
        if fac.estado == 'anulada':
            return Response({'error': 'No se puede editar una factura anulada.'}, status=400)

        ser = FacturaUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        d = ser.validated_data
        update_fields = []
        for field in ['cliente_nombre', 'cliente_cedula', 'cliente_correo',
                       'cliente_telefono', 'notas', 'descuento_pct', 'impuesto_pct']:
            if field in d:
                setattr(fac, field, d[field])
                update_fields.append(field)
        if update_fields:
            fac.save(update_fields=update_fields)

        if d.get('items'):
            _restore_factura_stock(fac)
            fac.items.all().delete()
            items_data = [
                {
                    'producto_id':    item['producto_id'],
                    'descripcion':    item.get('descripcion', ''),
                    'cantidad':       item['cantidad'],
                    'precio_unitario': item['precio_unitario'],
                    'descuento_item': item.get('descuento_item', 0),
                }
                for item in d['items']
            ]
            try:
                _create_factura_items_and_deduct(fac, items_data, fac.location)
            except Product.DoesNotExist as e:
                return Response({'error': str(e)}, status=400)
        elif any(f in update_fields for f in ['descuento_pct', 'impuesto_pct']):
            fac.recalcular_totales()

        fac.refresh_from_db()
        return Response({'data': FacturaDetailSerializer(fac).data})


class FacturaAnularView(APIView):
    permission_classes = [IsSuperUserOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        user = request.user
        tipo = _get_tipo(user)

        try:
            fac = Factura.objects.select_related('location').prefetch_related('items__producto').get(pk=pk)
        except Factura.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=404)

        if tipo == 1 and user.location and fac.location_id != user.location_id:
            return Response({'error': 'Sin permiso para esta factura.'}, status=403)

        if fac.estado == 'anulada':
            return Response({'error': 'La factura ya está anulada.'}, status=400)

        _restore_factura_stock(fac)
        fac.estado = 'anulada'
        fac.save(update_fields=['estado'])

        # If came from a quotation, revert it to 'aprobada' so it can be re-converted
        if fac.cotizacion:
            Cotizacion.objects.filter(pk=fac.cotizacion_id).update(estado='aprobada')

        return Response({'data': FacturaDetailSerializer(fac).data})

