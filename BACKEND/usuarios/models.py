# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UserManager


class Cargo(models.Model):
    idcargo = models.AutoField(primary_key=True)
    nombrecargo = models.CharField(max_length=30)
    estadocargo = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = 'cargo'

    def __str__(self):
        return self.nombrecargo


class Niveles(models.Model):
    idnivel = models.AutoField(primary_key=True)
    nombrenivel = models.CharField(max_length=50)
    estadonivel = models.IntegerField(default=1)
    prom = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niveles'

    def __str__(self):
        return self.nombrenivel


class Regional(models.Model):
    idregional = models.AutoField(primary_key=True)
    nombreregional = models.CharField(max_length=30)
    estadoregional = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = 'regional'

    def __str__(self):
        return self.nombreregional


class Usuario(models.Model):
    """
    Modelo de Usuario que contiene los datos personales.
    Reemplaza al antiguo modelo Colaboradores.
    """
    id = models.AutoField(primary_key=True)
    cedula = models.CharField(max_length=30, unique=True, null=False, blank=False)
    nombre_completo = models.CharField(max_length=100, null=False, blank=False)
    correo = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    sede = models.CharField(max_length=100, blank=True, null=True)
    cargo = models.ForeignKey('Cargo', models.SET_NULL, null=True, blank=True)
    nivel = models.ForeignKey('Niveles', models.SET_NULL, null=True, blank=True)
    regional = models.ForeignKey('Regional', models.SET_NULL, null=True, blank=True)
    estado = models.IntegerField(default=1)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        managed = True
        db_table = 'usuario'

    def __str__(self):
        return f"{self.nombre_completo} ({self.cedula})"


class Credenciales(AbstractBaseUser):
    """
    Modelo de autenticación que contiene las credenciales de acceso.
    Reemplaza al antiguo modelo Usuarios.
    Tiene relación OneToOne con el modelo Usuario.
    """
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=30, unique=True, null=False, blank=False)
    password = models.CharField(max_length=500)
    usuario_rel = models.OneToOneField(Usuario, models.CASCADE, null=True, blank=True, related_name='credenciales')
    estado = models.IntegerField(default=1)
    tipo_usuario = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_ultimo_acceso = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'usuario'
    REQUIRED_FIELDS = ['password']

    @property
    def is_staff(self):
        """Retorna True si es admin o super admin para acceso al admin de Django"""
        return self.tipo_usuario in [1, 4]
    
    @property
    def is_superuser(self):
        """Retorna True si es super admin"""
        return self.tipo_usuario == 4
    
    @property
    def is_active(self):
        """Retorna True si la credencial está activa"""
        return self.estado == 1
    
    def has_perm(self, perm, obj=None):
        """Retorna True si el usuario tiene el permiso especificado"""
        return self.tipo_usuario in [1, 4]
    
    def has_module_perms(self, app_label):
        """Retorna True si el usuario tiene permisos para ver el módulo"""
        return self.tipo_usuario in [1, 4]

    class Meta:
        managed = True
        db_table = 'credenciales'

    def __str__(self):
        return self.usuario


# Mantener los modelos antiguos para migración de datos (son obsoletos)
class Colaboradores(models.Model):
    idcolaborador = models.AutoField(primary_key=True)
    cccolaborador = models.CharField(max_length=30, null=False, blank=True, unique=True)
    nombrecolaborador = models.CharField(max_length=30)
    apellidocolaborador = models.CharField(max_length=30)
    cargocolaborador = models.ForeignKey('Cargo', models.SET_NULL, null=True)
    correocolaborador = models.CharField(max_length=50, blank=True, null=True)
    telefocolaborador = models.CharField(max_length=20, blank=True, null=True)
    estadocolaborador = models.IntegerField(default=1)
    nivelcolaborador = models.ForeignKey('Niveles', models.SET_NULL, null=True)
    regionalcolab = models.ForeignKey('Regional', models.SET_NULL, blank=True, null=True)
    sede = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'colaboradores'


class Usuarios(AbstractBaseUser):
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=30, null=True, blank=True, unique=True)
    password = models.CharField(max_length=500)
    idcolaboradoru = models.ForeignKey(Colaboradores, models.DO_NOTHING, null=True)
    estadousuario = models.IntegerField(default=1)
    tipousuario = models.IntegerField()

    objects = UserManager()

    USERNAME_FIELD = 'usuario'
    REQUIRED_FIELDS = [
        'password'
    ]

    @property
    def is_staff(self):
        """Retorna True si es admin o super admin para acceso al admin de Django"""
        return self.tipousuario in [1, 4]
    
    @property
    def is_superuser(self):
        """Retorna True si es super admin"""
        return self.tipousuario == 4
    
    @property
    def is_active(self):
        """Retorna True si el usuario está activo"""
        return self.estadousuario == 1
    
    def has_perm(self, perm, obj=None):
        """Retorna True si el usuario tiene el permiso especificado"""
        return self.tipousuario in [1, 4]
    
    def has_module_perms(self, app_label):
        """Retorna True si el usuario tiene permisos para ver el módulo"""
        return self.tipousuario in [1, 4]

    class Meta:
        managed = True
        db_table = 'usuarios'
