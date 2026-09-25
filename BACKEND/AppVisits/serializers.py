from decimal import Decimal
import re

from django.utils import timezone
from rest_framework import serializers
from django.core import signing
from django.urls import reverse
from .models import ClienteVisita, VisitaTecnica, ReporteVisita, EvidenciaFotografica, TipoVisita, CambioCostoVisita
from usuarios.models import Credenciales


# ─── helpers ──────────────────────────────────────────────────────────────────

class MonetaryNumberField(serializers.DecimalField):
    """Conserva Decimal al validar y representa dinero como número JSON."""

    def to_representation(self, value):
        if value is None:
            return None
        decimal_value = self.quantize(Decimal(str(value)))
        if decimal_value == decimal_value.to_integral_value():
            return int(decimal_value)
        return float(decimal_value)


class TecnicoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    correo = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()

    class Meta:
        model = Credenciales
        fields = ['id', 'usuario', 'nombre_completo', 'correo', 'telefono']

    def get_nombre_completo(self, obj):
        return obj.usuario_rel.nombre_completo if obj.usuario_rel else obj.usuario

    def get_correo(self, obj):
        return obj.usuario_rel.correo if obj.usuario_rel else ''

    def get_telefono(self, obj):
        return obj.usuario_rel.telefono if obj.usuario_rel else ''


class ClienteVisitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteVisita
        fields = '__all__'


class TipoVisitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoVisita
        fields = ['id', 'codigo', 'nombre', 'activo']

    def validate_codigo(self, value):
        if self.instance and value != self.instance.codigo:
            raise serializers.ValidationError('El código no puede modificarse porque identifica visitas históricas.')
        return value


class CambioCostoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = CambioCostoVisita
        fields = ['valor_anterior', 'valor_nuevo', 'motivo', 'cambiado_en', 'usuario_nombre']

    def get_usuario_nombre(self, obj):
        if not obj.usuario:
            return 'Usuario anterior'
        return obj.usuario.usuario_rel.nombre_completo if obj.usuario.usuario_rel else obj.usuario.usuario


class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenciaFotografica
        fields = ['id', 'imagen', 'descripcion', 'orden', 'subida_en']
        read_only_fields = ['subida_en']

    def validate_imagen(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('La imagen no puede superar 5 MB.')
        if getattr(value, 'content_type', '').lower() not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise serializers.ValidationError('Formato no permitido. Usa JPEG, PNG o WebP.')
        return value


class EvidenciaResponseSerializer(serializers.ModelSerializer):
    imagen = serializers.SerializerMethodField()

    class Meta:
        model = EvidenciaFotografica
        fields = ['id', 'imagen', 'descripcion', 'orden', 'subida_en', 'archivada_en']

    def get_imagen(self, obj):
        token = signing.dumps({
            'visit_id': obj.visita_id, 'photo_id': obj.pk,
            'version': obj.visita.pdf_link_version,
        }, salt='visita-foto-publica')
        return f'/api{reverse("visitas-foto-publica", args=[obj.visita_id, obj.pk])}?token={token}'


class ReporteSerializer(serializers.ModelSerializer):
    equipo_display = serializers.CharField(source='get_equipo_display', read_only=True)
    ubicacion_display = serializers.CharField(source='get_ubicacion_equipo_display', read_only=True)
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    firma_disponible = serializers.SerializerMethodField()
    firma_cliente = serializers.SerializerMethodField()

    class Meta:
        model = ReporteVisita
        exclude = ['firma_base64']
        read_only_fields = ['visita', 'creado_en', 'actualizado_en']

    def get_firma_disponible(self, obj):
        return bool(obj.firma_base64 or obj.firma_cliente)

    def get_firma_cliente(self, obj):
        if not obj.firma_cliente:
            return None
        token = signing.dumps({
            'visit_id': obj.visita_id, 'version': obj.visita.pdf_link_version,
        }, salt='visita-firma-publica')
        return f'/api{reverse("visitas-firma-publica", args=[obj.visita_id])}?token={token}'


# ─── list ──────────────────────────────────────────────────────────────────────

class VisitaListSerializer(serializers.ModelSerializer):
    valor_visita = MonetaryNumberField(max_digits=12, decimal_places=2, read_only=True)
    costo_inicial = MonetaryNumberField(max_digits=12, decimal_places=2, read_only=True)
    costo_final = MonetaryNumberField(source='valor_visita', max_digits=12, decimal_places=2, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_direccion = serializers.CharField(source='cliente.direccion', read_only=True)
    cliente_telefono = serializers.CharField(source='cliente.telefono', read_only=True)
    tecnico_nombre = serializers.SerializerMethodField()
    creado_por_nombre = serializers.SerializerMethodField()
    tipo_tarea_display = serializers.CharField(source='get_tipo_tarea_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tiene_reporte = serializers.SerializerMethodField()
    evidencias_count = serializers.SerializerMethodField()

    class Meta:
        model = VisitaTecnica
        fields = [
            'id', 'numero_tarea',
            'cliente_nombre', 'cliente_direccion', 'cliente_telefono',
            'tipo_tarea', 'tipo_tarea_display',
            'fecha', 'hora', 'valor_visita', 'costo_inicial', 'costo_final',
            'estado', 'estado_display',
            'tecnico_id', 'tecnico_nombre', 'creado_por_nombre',
            'tiene_reporte', 'evidencias_count',
            'fecha_creacion',
        ]

    def get_tecnico_nombre(self, obj):
        if not obj.tecnico:
            return None
        if obj.tecnico.usuario_rel:
            return obj.tecnico.usuario_rel.nombre_completo
        return obj.tecnico.usuario

    def get_creado_por_nombre(self, obj):
        if not obj.creado_por:
            return None
        return obj.creado_por.usuario_rel.nombre_completo if obj.creado_por.usuario_rel else obj.creado_por.usuario

    def get_tiene_reporte(self, obj):
        return hasattr(obj, 'reporte')

    def get_evidencias_count(self, obj):
        return obj.evidencias.count()


# ─── detail ────────────────────────────────────────────────────────────────────

class VisitaDetailSerializer(serializers.ModelSerializer):
    valor_visita = MonetaryNumberField(max_digits=12, decimal_places=2, read_only=True)
    costo_inicial = MonetaryNumberField(max_digits=12, decimal_places=2, read_only=True)
    costo_final = MonetaryNumberField(source='valor_visita', max_digits=12, decimal_places=2, read_only=True)
    offline_sync_supported = serializers.SerializerMethodField()
    sync_version = serializers.SerializerMethodField()
    creado_por_nombre = serializers.SerializerMethodField()
    cambios_costo = CambioCostoSerializer(many=True, read_only=True)
    pdf_disponible = serializers.SerializerMethodField()
    pdf_nombre = serializers.SerializerMethodField()

    def get_pdf_disponible(self, obj):
        if not obj.pdf_final or obj.pdf_estado == 'error':
            return False
        if obj.pdf_source_hash:
            from .views import _pdf_source_hash
            return obj.pdf_source_hash == _pdf_source_hash(obj)
        return True

    def get_pdf_nombre(self, obj):
        if not self.get_pdf_disponible(obj):
            return None
        from .views import _pdf_filename
        return _pdf_filename(obj)

    def get_creado_por_nombre(self, obj):
        if not obj.creado_por:
            return None
        return obj.creado_por.usuario_rel.nombre_completo if obj.creado_por.usuario_rel else obj.creado_por.usuario

    def get_offline_sync_supported(self, obj):
        return True

    def get_sync_version(self, obj):
        from .sync_version import visit_sync_version
        return visit_sync_version(obj)
    cliente = ClienteVisitaSerializer(read_only=True)
    tecnico = TecnicoSerializer(read_only=True)
    reporte = ReporteSerializer(read_only=True)
    evidencias = EvidenciaResponseSerializer(many=True, read_only=True)
    tipo_tarea_display = serializers.CharField(source='get_tipo_tarea_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = VisitaTecnica
        exclude = ['pdf_final']


# ─── create ────────────────────────────────────────────────────────────────────

class VisitaCreateSerializer(serializers.Serializer):
    # Cliente
    cliente_nombre = serializers.CharField(
        max_length=200,
        error_messages={'required': 'Este campo es obligatorio.', 'blank': 'Este campo es obligatorio.'},
    )
    cliente_identificacion = serializers.CharField(
        max_length=15, required=False, allow_blank=True, default='',
    )
    cliente_telefono = serializers.CharField(
        max_length=15,
        error_messages={'required': 'Este campo es obligatorio.', 'blank': 'Este campo es obligatorio.'},
    )
    cliente_correo = serializers.EmailField(
        max_length=100,
        error_messages={
            'required': 'Este campo es obligatorio.',
            'blank': 'Este campo es obligatorio.',
            'invalid': 'Ingrese un correo electrónico válido.',
        },
    )
    cliente_direccion = serializers.CharField(
        error_messages={'required': 'Este campo es obligatorio.', 'blank': 'Este campo es obligatorio.'},
    )
    cliente_indicaciones_llegada = serializers.CharField(required=False, allow_blank=True, default='')
    # Visita
    tipo_tarea = serializers.CharField(
        max_length=50,
        error_messages={'required': 'Este campo es obligatorio.', 'blank': 'Este campo es obligatorio.'},
    )
    fecha = serializers.DateField(error_messages={'required': 'Este campo es obligatorio.'})
    hora = serializers.TimeField(error_messages={'required': 'Este campo es obligatorio.'})
    descripcion = serializers.CharField(required=False, allow_blank=True, default='')
    observaciones_iniciales = serializers.CharField(required=False, allow_blank=True, default='')
    valor_visita = MonetaryNumberField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal('0'),
    )
    tecnico_id = serializers.IntegerField(
        required=True,
        allow_null=False,
        error_messages={
            'required': 'Debe seleccionar un técnico.',
            'null': 'Debe seleccionar un técnico.',
            'invalid': 'Debe seleccionar un técnico válido.',
        },
    )

    def validate_cliente_identificacion(self, value):
        value = value.strip()
        if not value:
            return ''
        if not re.fullmatch(r'[0-9]+', value):
            raise serializers.ValidationError('La cédula solo puede contener números.')
        if not 6 <= len(value) <= 15:
            raise serializers.ValidationError('La cédula debe contener entre 6 y 15 números.')
        return value

    def validate_tipo_tarea(self, value):
        if not TipoVisita.objects.filter(codigo=value, activo=True).exists():
            raise serializers.ValidationError('Selecciona un tipo de visita activo.')
        return value

    def validate_cliente_telefono(self, value):
        value = value.strip()
        if not re.fullmatch(r'[0-9]+', value):
            raise serializers.ValidationError('El número de celular solo puede contener números.')
        if not 7 <= len(value) <= 15:
            raise serializers.ValidationError('El número de celular debe contener entre 7 y 15 números.')
        return value

    def validate_cliente_correo(self, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value):
            raise serializers.ValidationError('Ingrese un correo electrónico válido.')
        return value

    def validate_fecha(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('La fecha de la visita no puede ser anterior al día actual.')
        return value

    def validate_tecnico_id(self, value):
        if not Credenciales.objects.filter(pk=value, tipo_usuario=1, estado=1).exists():
            raise serializers.ValidationError('Debe seleccionar un técnico válido y activo.')
        return value

    def create(self, validated_data):
        cliente = ClienteVisita.objects.create(
            nombre=validated_data['cliente_nombre'],
            identificacion=validated_data.get('cliente_identificacion', ''),
            telefono=validated_data.get('cliente_telefono', ''),
            correo=validated_data.get('cliente_correo', ''),
            direccion=validated_data['cliente_direccion'],
            indicaciones_llegada=validated_data.get('cliente_indicaciones_llegada', ''),
        )
        tecnico_id = validated_data.get('tecnico_id')
        tecnico = Credenciales.objects.get(id=tecnico_id, tipo_usuario=1, estado=1)
        creado_por = self.context.get('request').user if self.context.get('request') else None
        visita = VisitaTecnica.objects.create(
            cliente=cliente,
            tecnico=tecnico,
            tipo_tarea=validated_data['tipo_tarea'],
            tipo_tarea_etiqueta=TipoVisita.objects.get(codigo=validated_data['tipo_tarea']).nombre,
            fecha=validated_data['fecha'],
            hora=validated_data['hora'],
            descripcion=validated_data.get('descripcion', ''),
            observaciones_iniciales=validated_data.get('observaciones_iniciales', ''),
            valor_visita=validated_data.get('valor_visita'),
            costo_inicial=validated_data.get('valor_visita'),
            creado_por=creado_por,
        )
        return visita


class VisitaUpdateSerializer(serializers.ModelSerializer):
    valor_visita = MonetaryNumberField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )
    cliente_indicaciones_llegada = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = VisitaTecnica
        fields = ['tipo_tarea', 'fecha', 'hora', 'descripcion', 'observaciones_iniciales', 'valor_visita', 'estado', 'tecnico', 'cliente_indicaciones_llegada']

    def validate_tipo_tarea(self, value):
        if not TipoVisita.objects.filter(codigo=value, activo=True).exists():
            raise serializers.ValidationError('Selecciona un tipo de visita activo.')
        return value

    def update(self, instance, validated_data):
        directions = validated_data.pop('cliente_indicaciones_llegada', None)
        if 'tipo_tarea' in validated_data and validated_data['tipo_tarea'] != instance.tipo_tarea:
            instance.tipo_tarea_etiqueta = TipoVisita.objects.get(codigo=validated_data['tipo_tarea']).nombre
            validated_data['tipo_tarea_etiqueta'] = instance.tipo_tarea_etiqueta
        instance = super().update(instance, validated_data)
        if directions is not None:
            instance.cliente.indicaciones_llegada = directions
            instance.cliente.save(update_fields=['indicaciones_llegada'])
        return instance

    def validate_fecha(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('La fecha de la visita no puede ser anterior al día actual.')
        return value

    def validate_tecnico(self, value):
        if value is None or value.tipo_usuario != 1 or value.estado != 1:
            raise serializers.ValidationError('Debe seleccionar un técnico válido y activo.')
        return value

    def validate(self, attrs):
        if self.instance and self.instance.estado == VisitaTecnica.ESTADO_FINALIZADA:
            raise serializers.ValidationError('No se puede modificar una visita que ya está finalizada.')
        return attrs

    def validate_estado(self, value):
        if value == VisitaTecnica.ESTADO_FINALIZADA:
            raise serializers.ValidationError('Utiliza el endpoint finalizar para completar la visita y generar su reporte.')
        return value


# ─── report ────────────────────────────────────────────────────────────────────

class ReporteCreateSerializer(serializers.ModelSerializer):
    valor_servicio = MonetaryNumberField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0')
    )

    class Meta:
        model = ReporteVisita
        exclude = ['visita', 'creado_en', 'actualizado_en']
