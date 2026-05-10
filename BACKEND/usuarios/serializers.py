from rest_framework import serializers
from usuarios.models import Usuario, Cargo, Niveles, Regional


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'cedula', 'nombre_completo', 'correo', 'telefono', 'sede', 'estado']


class UsuarioListadoSerializer(serializers.ModelSerializer):
    nombre_cargo = serializers.CharField(source='cargo.nombrecargo', allow_null=True, default=None)
    nombre_nivel = serializers.CharField(source='nivel.nombrenivel', allow_null=True, default=None)
    nombre_regional = serializers.CharField(source='regional.nombreregional', allow_null=True, default=None)

    class Meta:
        model = Usuario
        fields = [
            'id',
            'cedula',
            'nombre_completo',
            'correo',
            'telefono',
            'sede',
            'nombre_cargo',
            'nombre_nivel',
            'nombre_regional',
            'estado',
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