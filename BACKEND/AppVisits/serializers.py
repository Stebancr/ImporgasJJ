from rest_framework import serializers
from .models import ClienteVisita, VisitaTecnica, ReporteVisita, EvidenciaFotografica
from usuarios.models import Credenciales


# ─── helpers ──────────────────────────────────────────────────────────────────

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


class ReporteSerializer(serializers.ModelSerializer):
    equipo_display = serializers.CharField(source='get_equipo_display', read_only=True)
    ubicacion_display = serializers.CharField(source='get_ubicacion_equipo_display', read_only=True)
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    firma_disponible = serializers.SerializerMethodField()

    class Meta:
        model = ReporteVisita
        fields = '__all__'
        read_only_fields = ['visita', 'creado_en', 'actualizado_en']

    def get_firma_disponible(self, obj):
        return bool(obj.firma_base64 or obj.firma_cliente)


# ─── list ──────────────────────────────────────────────────────────────────────

class VisitaListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_direccion = serializers.CharField(source='cliente.direccion', read_only=True)
    cliente_telefono = serializers.CharField(source='cliente.telefono', read_only=True)
    tecnico_nombre = serializers.SerializerMethodField()
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
            'fecha', 'hora',
            'estado', 'estado_display',
            'tecnico_id', 'tecnico_nombre',
            'tiene_reporte', 'evidencias_count',
            'fecha_creacion',
        ]

    def get_tecnico_nombre(self, obj):
        if not obj.tecnico:
            return None
        if obj.tecnico.usuario_rel:
            return obj.tecnico.usuario_rel.nombre_completo
        return obj.tecnico.usuario

    def get_tiene_reporte(self, obj):
        return hasattr(obj, 'reporte')

    def get_evidencias_count(self, obj):
        return obj.evidencias.count()


# ─── detail ────────────────────────────────────────────────────────────────────

class VisitaDetailSerializer(serializers.ModelSerializer):
    cliente = ClienteVisitaSerializer(read_only=True)
    tecnico = TecnicoSerializer(read_only=True)
    reporte = ReporteSerializer(read_only=True)
    evidencias = EvidenciaSerializer(many=True, read_only=True)
    tipo_tarea_display = serializers.CharField(source='get_tipo_tarea_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = VisitaTecnica
        fields = '__all__'


# ─── create ────────────────────────────────────────────────────────────────────

class VisitaCreateSerializer(serializers.Serializer):
    # Cliente
    cliente_nombre = serializers.CharField(max_length=200)
    cliente_identificacion = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    cliente_telefono = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    cliente_correo = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    cliente_direccion = serializers.CharField()
    # Visita
    tipo_tarea = serializers.ChoiceField(choices=VisitaTecnica.TIPO_TAREA_CHOICES)
    fecha = serializers.DateField()
    hora = serializers.TimeField()
    descripcion = serializers.CharField(required=False, allow_blank=True, default='')
    observaciones_iniciales = serializers.CharField(required=False, allow_blank=True, default='')
    tecnico_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def create(self, validated_data):
        cliente = ClienteVisita.objects.create(
            nombre=validated_data['cliente_nombre'],
            identificacion=validated_data.get('cliente_identificacion', ''),
            telefono=validated_data.get('cliente_telefono', ''),
            correo=validated_data.get('cliente_correo', ''),
            direccion=validated_data['cliente_direccion'],
        )
        tecnico_id = validated_data.get('tecnico_id')
        tecnico = Credenciales.objects.filter(id=tecnico_id).first() if tecnico_id else None
        creado_por = self.context.get('request').user if self.context.get('request') else None
        visita = VisitaTecnica.objects.create(
            cliente=cliente,
            tecnico=tecnico,
            tipo_tarea=validated_data['tipo_tarea'],
            fecha=validated_data['fecha'],
            hora=validated_data['hora'],
            descripcion=validated_data.get('descripcion', ''),
            observaciones_iniciales=validated_data.get('observaciones_iniciales', ''),
            creado_por=creado_por,
        )
        return visita


class VisitaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitaTecnica
        fields = ['tipo_tarea', 'fecha', 'hora', 'descripcion', 'observaciones_iniciales', 'estado', 'tecnico']

    def validate_estado(self, value):
        if value == VisitaTecnica.ESTADO_FINALIZADA:
            raise serializers.ValidationError('Utiliza el endpoint finalizar para completar la visita y generar su reporte.')
        return value


# ─── report ────────────────────────────────────────────────────────────────────

class ReporteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReporteVisita
        exclude = ['visita', 'creado_en', 'actualizado_en']
