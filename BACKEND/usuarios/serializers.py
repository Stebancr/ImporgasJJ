from rest_framework import serializers
from usuarios.models import Usuario, Cargo, Niveles, Regional


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'cedula', 'nombre_completo', 'correo', 'telefono', 'sede', 'estado']


class UsuarioListadoSerializer(serializers.ModelSerializer):
    nombre_cargo = serializers.CharField(source='cargo.nombrecargo', allow_null=True, default=None)

    # Fields from the related Credenciales record
    usuario = serializers.SerializerMethodField()
    tipo_usuario = serializers.SerializerMethodField()
    location_id = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    def get_usuario(self, obj):
        creds = getattr(obj, 'credenciales', None)
        return creds.usuario if creds else None

    def get_tipo_usuario(self, obj):
        creds = getattr(obj, 'credenciales', None)
        return creds.tipo_usuario if creds is not None else 0

    def get_location_id(self, obj):
        creds = getattr(obj, 'credenciales', None)
        return creds.location_id if creds else None

    def get_location_name(self, obj):
        creds = getattr(obj, 'credenciales', None)
        if creds and creds.location_id:
            try:
                loc = creds.location
                return f"{loc.name} — {loc.city}" if loc else None
            except Exception:
                pass
        return None

    class Meta:
        model = Usuario
        fields = [
            'id',
            'cedula',
            'nombre_completo',
            'correo',
            'telefono',
            'sede',
            'cargo',
            'nombre_cargo',
            'estado',
            'usuario',
            'tipo_usuario',
            'location_id',
            'location_name',
        ]


class CargoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cargo
        fields = ['idcargo', 'nombrecargo', 'estadocargo']


class NivelesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niveles
        fields = ['idnivel', 'nombrenivel', 'estadonivel', 'prom']


class RegionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regional
        fields = ['idregional', 'nombreregional', 'estadoregional']