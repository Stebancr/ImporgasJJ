from django.core import signing
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Delivery
from .documents import document_link, ensure_document
from .service import source_for
from usuarios.permissions import IsAdminUser
from django.utils import timezone
from django.db.models import F


class DocumentView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        try:
            data=signing.loads(request.query_params.get('token',''),salt='transactional-document',max_age=7*86400)
            if data.get('delivery')!=str(pk):
                raise signing.BadSignature()
        except signing.BadSignature:
            return Response({'detail':'Enlace inválido o vencido.'},status=403)
        delivery=Delivery.objects.filter(pk=pk).first()
        if not delivery:
            return Response({'detail':'Documento no disponible.'},status=404)
        try:
            source=source_for(delivery.kind,delivery.object_id)
            if delivery.kind=='visit' and data.get('version')!=source.pdf_link_version:
                return Response({'detail':'Enlace revocado.'},status=403)
            if delivery.kind=='order' and source.wompi_status!='APPROVED':
                return Response({'detail':'Documento no disponible.'},status=404)
            # Reading a link must not regenerate missing documents or mutate data.
            file=delivery.document if delivery.kind=='order' else source.pdf_final
            if not file or not file.storage.exists(file.name):
                return Response({'detail':'Documento no disponible.'},status=404)
            if delivery.kind=='visit':
                ensure_document(delivery,source)
            response=FileResponse(file.open('rb'),as_attachment=request.query_params.get('download')=='1',
                filename='comprobante.pdf' if delivery.kind=='order' else 'informe-servicio.pdf',content_type='application/pdf')
        except Exception:
            return Response({'detail':'Documento no disponible.'},status=404)
        response['Cache-Control']='private, no-store'
        response['X-Robots-Tag']='noindex, nofollow, noarchive'
        response['Referrer-Policy']='no-referrer'
        response['X-Content-Type-Options']='nosniff'
        return response


class RenewLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request,pk):
        delivery=Delivery.objects.filter(pk=pk).first()
        if not delivery:
            return Response({'detail':'Documento no disponible.'},status=404)
        try:
            source=source_for(delivery.kind,delivery.object_id)
        except Exception:
            return Response({'detail':'Documento no disponible.'},status=404)
        admin=getattr(request.user,'tipo_usuario',0) in (1,4)
        owner=delivery.kind=='order' and source.user_id==request.user.pk
        if not admin and not owner:
            return Response({'detail':'No tienes permiso para este documento.'},status=403)
        if delivery.kind=='order' and source.wompi_status!='APPROVED':
            return Response({'detail':'Documento no disponible.'},status=409)
        try:
            ensure_document(delivery,source)
            return Response({'url':document_link(delivery)})
        except Exception:
            return Response({'detail':'Documento no disponible.'},status=409)


class DeliveryAuditView(APIView):
    permission_classes=[IsAdminUser]

    def get(self,request):
        records=Delivery.objects.order_by('-created_at')
        if request.query_params.get('kind') in ('order','visit'):
            records=records.filter(kind=request.query_params['kind'])
        if request.query_params.get('object_id','').isdigit():
            records=records.filter(object_id=request.query_params['object_id'])
        return Response({'data':list(records.values('id','kind','object_id','recipient','state','attempts','last_error','created_at','sent_at','provider_id')[:100])})


class RetryDeliveryView(APIView):
    permission_classes=[IsAdminUser]

    def post(self,request,pk):
        changed=Delivery.objects.filter(pk=pk,state='failed').update(state='pending',max_attempts=F('attempts')+3,next_attempt_at=timezone.now())
        if not changed:
            return Response({'detail':'Solo se reintentan fallidos; los enviados o inciertos requieren revisión.'},status=409)
        from .tasks import deliver
        try:deliver.apply_async(args=[str(pk)],retry=False)
        except Exception:pass  # Beat recovers the durable pending event.
        return Response({'detail':'Reintento registrado.'},status=202)
