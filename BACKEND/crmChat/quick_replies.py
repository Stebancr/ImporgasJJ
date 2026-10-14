"""Private reusable drafts; selecting or previewing NEVER sends a message."""
import re
import json
from pathlib import Path
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import QuickReply, QuickReplyPreference, ChatAuditEvent, ChatSession
from .attachment_validation import validate_chat_upload, upload_sha256, CHANNEL_MEDIA, ensure_channel_media

VARIABLES = {'nombre_cliente', 'nombre_agente', 'numero_visita', 'fecha_visita',
             'costo_final', 'enlace_pdf', 'nombre_producto', 'enlace_producto'}
PATTERN = re.compile(r'{{\s*([a-z_]+)\s*}}')


def render_template(template, values):
    required = set(PATTERN.findall(template.text))
    missing = sorted(key for key in required if not str(values.get(key, '')).strip())
    if missing:
        raise ValueError('Completa las variables: ' + ', '.join(missing))
    text = PATTERN.sub(lambda match: str(values[match[1]]).strip(), template.text)
    if '{{' in text or '}}' in text or len(text) > 4000:
        raise ValueError('Variables inválidas o mensaje demasiado largo.')
    return text


class QuickReplySerializer(serializers.ModelSerializer):
    variables = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    favorite = serializers.SerializerMethodField()
    last_used_at = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = QuickReply
        fields = ['id', 'name', 'category', 'channels', 'text', 'active', 'variables',
                  'author_name', 'created_at', 'updated_at', 'favorite', 'last_used_at',
                  'attachment_url', 'attachment_metadata']
        read_only_fields = ['attachment_metadata']

    def get_variables(self, obj):
        return sorted(set(PATTERN.findall(obj.text)))

    def get_author_name(self, obj):
        return getattr(obj.author, 'usuario', '') if obj.author_id else ''

    def _preference(self, obj):
        return next((p for p in obj.preferences.all() if p.user_id == self.context['request'].user.pk), None)

    def get_favorite(self, obj):
        return bool(getattr(self._preference(obj), 'favorite', False))

    def get_last_used_at(self, obj):
        return getattr(self._preference(obj), 'last_used_at', None)

    def get_attachment_url(self, obj):
        return f'/api/crm-chat/templates/{obj.pk}/file/' if obj.attachment else ''

    def validate_channels(self, value):
        if not isinstance(value, list) or not value or any(c not in CHANNEL_MEDIA for c in value):
            raise serializers.ValidationError('Selecciona al menos un canal válido.')
        return sorted(set(value))

    def validate_text(self, value):
        unknown = set(PATTERN.findall(value)) - VARIABLES
        residue = PATTERN.sub('', value)
        if not value.strip() or len(value) > 4000 or unknown or '{{' in residue or '}}' in residue:
            raise serializers.ValidationError('Texto o variables inválidos. Usa las variables disponibles.')
        return value


class QuickReplyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'crm_upload'

    def allowed(self, request):
        return getattr(request.user, 'tipo_usuario', 0) in (1, 4)

    def serialize(self, obj, request, many=False):
        return QuickReplySerializer(obj, many=many, context={'request': request}).data

    def get(self, request, pk=None):
        if not self.allowed(request):
            return Response({'error': 'No autorizado'}, status=403)
        qs = QuickReply.objects.select_related('author').prefetch_related('preferences').order_by('category', 'name')
        if pk:
            obj = qs.filter(pk=pk).first()
            return Response(self.serialize(obj, request)) if obj else Response(status=404)
        query = request.query_params.get('search', '')[:100]
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(category__icontains=query) | Q(text__icontains=query))
        if request.query_params.get('channel'):
            qs = qs.filter(channels__contains=[request.query_params['channel']], active=True)
        return Response(self.serialize(qs, request, many=True))

    def post(self, request, pk=None, action=None):
        if action not in (None, 'favorite', 'preview'):
            return Response(status=404)
        if not self.allowed(request):
            return Response({'error': 'No autorizado'}, status=403)
        obj = QuickReply.objects.filter(pk=pk).first() if pk else None
        if pk and not obj:
            return Response(status=404)
        if action == 'favorite':
            pref, _ = QuickReplyPreference.objects.get_or_create(template=obj, user=request.user)
            pref.favorite = not pref.favorite
            pref.save(update_fields=['favorite'])
            return Response({'favorite': pref.favorite})
        if action == 'preview':
            session = ChatSession.objects.filter(pk=request.data.get('session_id')).first()
            if not session or not obj.active or session.channel not in obj.channels:
                return Response({'error': 'Plantilla inactiva o incompatible con la conversación.'}, status=400)
            values = request.data.get('variables', {})
            if not isinstance(values, dict):
                return Response({'error': 'Variables inválidas'}, status=400)
            try:
                text = render_template(obj, values)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=400)
            return Response({'text': text, 'attachment_url': self.serialize(obj, request)['attachment_url']})
        if getattr(request.user, 'tipo_usuario', 0) != 4:
            return Response({'error': 'Solo administradores pueden administrar plantillas.'}, status=403)
        data = request.data.copy()
        if isinstance(data.get('channels'), str):
            try:
                data['channels'] = json.loads(data['channels'])
            except ValueError:
                return Response({'error': 'Canales inválidos'}, status=400)
        # QueryDict list semantics are inappropriate for a JSONField.
        data = {key: data.get(key) for key in ('name', 'category', 'channels', 'text', 'active') if key in data}
        serializer = QuickReplySerializer(obj, data=data, partial=bool(obj), context={'request': request})
        serializer.is_valid(raise_exception=True)
        upload = request.FILES.get('file')
        metadata = None
        if upload:
            try:
                name, mime, kind = validate_chat_upload(upload)
                for channel in serializer.validated_data.get('channels', obj.channels if obj else []):
                    ensure_channel_media(channel, kind)
                metadata = {'name': name, 'mime_type': mime, 'size': upload.size, 'sha256': upload_sha256(upload), 'type': kind}
            except ValueError as exc:
                return Response({'error': str(exc)}, status=400)
        if obj and obj.attachment and not upload:
            try:
                for channel in serializer.validated_data.get('channels', obj.channels):
                    ensure_channel_media(channel, obj.attachment_metadata.get('type'))
            except ValueError as exc:
                return Response({'error': str(exc)}, status=400)
        obj = serializer.save(**({'author': request.user} if obj is None else {}))
        if upload:
            obj.attachment = upload
            obj.attachment_metadata = metadata
            obj.save(update_fields=['attachment', 'attachment_metadata'])
        if request.data.get('remove_attachment') in (True, 'true'):
            obj.attachment = ''  # Historical files are retained, never deleted by editing.
            obj.attachment_metadata = {}
            obj.save(update_fields=['attachment', 'attachment_metadata'])
        ChatAuditEvent.objects.create(actor=request.user, action='template.updated' if pk else 'template.created', details={'template_id': obj.pk})
        return Response(self.serialize(obj, request), status=200 if pk else 201)

    def patch(self, request, pk):
        return self.post(request, pk)


class QuickReplyFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if getattr(request.user, 'tipo_usuario', 0) not in (1, 4):
            return Response(status=403)
        obj = QuickReply.objects.filter(pk=pk).first()
        if not obj or not obj.attachment:
            return Response(status=404)
        response = FileResponse(obj.attachment.open('rb'), as_attachment=True,
                                filename=Path(obj.attachment_metadata.get('name', 'adjunto')).name,
                                content_type=obj.attachment_metadata.get('mime_type', 'application/octet-stream'))
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
