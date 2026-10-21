"""Transactional administration editor. Files removed from the gallery are retained on disk."""
import hashlib
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import translation
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from usuarios.permissions import IsAdminUser
from .models import Product, ProductImage, ProductStock, ProductSpec, SpecAttribute, Location, ProductEditorOperation
from .serializers import ProductCreateSerializer, ProductDetailSerializer, ProductImageUploadSerializer


class GalleryItem(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    file = serializers.CharField(required=False, max_length=40)
    alt_text = serializers.CharField(max_length=255, allow_blank=True, default='')

    def validate(self, data):
        if ('id' in data) == ('file' in data):
            raise serializers.ValidationError('Selecciona una imagen existente o un archivo nuevo.')
        return data


class StockItem(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    quantity = serializers.IntegerField(min_value=0, max_value=2147483647)


class SpecItem(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    name = serializers.CharField(required=False, max_length=100)
    value = serializers.CharField(max_length=255)

    def validate(self, data):
        if not data.get('id') and not data.get('name'):
            raise serializers.ValidationError('Indica el nombre de la característica.')
        return data


class EditorInput(serializers.Serializer):
    key = serializers.UUIDField()
    product = serializers.DictField()
    images = GalleryItem(many=True, max_length=30)
    primary = serializers.IntegerField(min_value=0, allow_null=True)
    stocks = StockItem(many=True)
    specs = SpecItem(many=True, max_length=100)
    updated_at = serializers.CharField(required=False)


class ProductEditorView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser]

    def dispatch(self, *args, **kwargs):
        with translation.override('es'):
            return super().dispatch(*args, **kwargs)

    def post(self, request, pk=None):
        try:
            raw = json.loads(request.data.get('payload', ''))
        except (ValueError, TypeError):
            raise serializers.ValidationError({'detail': 'Formulario inválido.'})
        form = EditorInput(data=raw)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode())
        uploads = {}
        for name in sorted(request.FILES):
            file = request.FILES[name]
            digest.update(name.encode())
            for chunk in file.chunks():
                digest.update(chunk)
            file.seek(0)
            upload = ProductImageUploadSerializer(data={'image': file})
            if not upload.is_valid():
                raise serializers.ValidationError({'images': 'Archivo inválido. Usa una imagen JPG, PNG o WebP válida de hasta 5 MB.'})
            uploads[name] = upload.validated_data['image']
        fingerprint = digest.hexdigest()
        written = []
        try:
            with transaction.atomic():
                # Serialize retries from this administrator, including creation requests.
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                operation = ProductEditorOperation.objects.filter(key=data['key']).first()
                if operation:
                    if operation.user_id != request.user.pk or operation.fingerprint != fingerprint or (pk and pk != operation.product_id):
                        return Response({'detail': 'La solicitud cambió. Revisa el producto antes de guardar otra vez.'}, status=409)
                    return Response({'data': ProductDetailSerializer(operation.product, context={'request': request}).data})
                product = get_object_or_404(Product.objects.select_for_update(), pk=pk) if pk else None
                if product and data.get('updated_at') != product.updated_at.isoformat().replace('+00:00', 'Z'):
                    return Response({'detail': 'Otro usuario modificó el producto. Conserva tu borrador y vuelve a abrirlo para revisar los cambios.'}, status=409)
                editor = ProductCreateSerializer(product, data=data['product'])
                editor.is_valid(raise_exception=True)
                existing = {image.pk: image for image in product.images.all()} if product else {}
                specs = {spec.pk: spec for spec in product.specifications.all()} if product else {}
                keys = [str(item.get('id', item.get('file'))) for item in data['images']]
                if len(keys) != len(set(keys)):
                    raise serializers.ValidationError({'images': 'No repitas imágenes en la galería.'})
                if data['images'] and (data['primary'] is None or data['primary'] >= len(data['images'])):
                    raise serializers.ValidationError({'images': 'Selecciona una imagen principal.'})
                for item in data['images']:
                    if ('id' in item and item['id'] not in existing) or ('file' in item and item['file'] not in uploads):
                        raise serializers.ValidationError({'images': 'La imagen no pertenece a este producto o falta el archivo.'})
                if set(uploads) != {item['file'] for item in data['images'] if 'file' in item}:
                    raise serializers.ValidationError({'images': 'Los archivos no coinciden con la galería.'})
                for item in data['specs']:
                    if item.get('id') and item['id'] not in specs:
                        raise serializers.ValidationError({'specs': 'La característica no pertenece al producto.'})
                if len({s['location'].pk for s in data['stocks']}) != len(data['stocks']):
                    raise serializers.ValidationError({'stocks': 'No repitas sedes.'})
                product = editor.save()
                keep = []
                product.images.update(is_primary=False)
                for index, item in enumerate(data['images']):
                    image = existing.get(item.get('id')) or ProductImage(product=product)
                    if 'file' in item:
                        image.image = uploads[item['file']]
                    image.alt_text = item['alt_text']
                    image.order = index
                    image.is_primary = index == data['primary']
                    try:
                        image.save()
                    finally:
                        if 'file' in item and image.image._committed:
                            written.append((image.image.storage, image.image.name))
                    keep.append(image.pk)
                # Retaining removed blobs avoids irreversible filesystem changes on rollback.
                product.images.exclude(pk__in=keep).delete()
                for item in data['stocks']:
                    ProductStock.objects.update_or_create(product=product, location=item['location'], defaults={'quantity': item['quantity']})
                retained_specs = []
                attributes = set()
                for index, item in enumerate(data['specs']):
                    spec = specs.get(item.get('id'))
                    attribute = spec.attribute if spec else SpecAttribute.objects.get_or_create(name=item['name'])[0]
                    if attribute.pk in attributes:
                        raise serializers.ValidationError({'specs': 'No repitas características.'})
                    attributes.add(attribute.pk)
                    spec = spec or product.specifications.filter(attribute=attribute).first() or ProductSpec(product=product, attribute=attribute)
                    spec.value, spec.order = item['value'], index
                    spec.save()
                    retained_specs.append(spec.pk)
                product.specifications.exclude(pk__in=retained_specs).delete()
                ProductEditorOperation.objects.create(key=data['key'], user=request.user, product=product, fingerprint=fingerprint)
                product.refresh_from_db()
                result = ProductDetailSerializer(product, context={'request': request}).data
            return Response({'data': result}, status=200 if pk else 201)
        except Exception:
            for storage, name in written:
                storage.delete(name)
            raise
