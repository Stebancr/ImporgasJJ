import random
from django.db import models


def _generar_numero_tarea():
    return str(random.randint(1000000, 9999999))


class ClienteVisita(models.Model):
    """Información del cliente para una visita técnica."""
    nombre = models.CharField(max_length=200)
    identificacion = models.CharField(max_length=30, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.CharField(max_length=100, blank=True)
    direccion = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visita_cliente'
        verbose_name = 'Cliente de Visita'
        verbose_name_plural = 'Clientes de Visita'

    def __str__(self):
        return f"{self.nombre}"


class VisitaTecnica(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_EN_PROCESO = 'en_proceso'
    ESTADO_FINALIZADA = 'finalizada'
    ESTADO_CANCELADA = 'cancelada'

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_PROCESO, 'En Proceso'),
        (ESTADO_FINALIZADA, 'Finalizada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    TIPO_TAREA_CHOICES = [
        ('mantenimiento', 'Mantenimiento Preventivo'),
        ('instalacion', 'Instalación'),
        ('reparacion', 'Reparación'),
        ('revision', 'Revisión Técnica'),
        ('visita_tecnica', 'Visita Técnica Perímetro Urbano'),
        ('garantia', 'Garantía'),
    ]

    numero_tarea = models.CharField(max_length=20, unique=True, blank=True)
    tecnico = models.ForeignKey(
        'usuarios.Credenciales',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visitas_asignadas',
        verbose_name='Técnico asignado',
    )
    cliente = models.ForeignKey(
        ClienteVisita,
        on_delete=models.CASCADE,
        related_name='visitas',
    )
    tipo_tarea = models.CharField(max_length=50, choices=TIPO_TAREA_CHOICES)
    fecha = models.DateField()
    hora = models.TimeField()
    descripcion = models.TextField(blank=True)
    observaciones_iniciales = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    creado_por = models.ForeignKey(
        'usuarios.Credenciales',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visitas_creadas',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'visita_tecnica'
        verbose_name = 'Visita Técnica'
        verbose_name_plural = 'Visitas Técnicas'
        ordering = ['fecha', 'hora']

    def __str__(self):
        return f"#{self.numero_tarea} — {self.cliente.nombre} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        if not self.numero_tarea:
            # Ensure uniqueness
            while True:
                num = _generar_numero_tarea()
                if not VisitaTecnica.objects.filter(numero_tarea=num).exists():
                    self.numero_tarea = num
                    break
        super().save(*args, **kwargs)


class ReporteVisita(models.Model):
    EQUIPO_CHOICES = [
        ('estufa', 'Estufa'),
        ('horno', 'Horno'),
        ('calentador', 'Calentador'),
        ('parrilla', 'Parrilla'),
        ('caldera', 'Caldera'),
        ('calefactor', 'Calefactor'),
        ('otro', 'Otro'),
    ]
    UBICACION_CHOICES = [
        ('cocina', 'Cocina'),
        ('patio', 'Patio'),
        ('balcon', 'Balcón'),
        ('exterior', 'Exterior'),
        ('sotano', 'Sótano'),
        ('otro', 'Otro'),
    ]
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('credito', 'Crédito'),
        ('otro', 'Otro'),
    ]

    visita = models.OneToOneField(
        VisitaTecnica,
        on_delete=models.CASCADE,
        related_name='reporte',
    )
    persona_atiende = models.CharField(max_length=200)
    equipo = models.CharField(max_length=50, choices=EQUIPO_CHOICES)
    equipo_otro = models.CharField(max_length=100, blank=True)
    ubicacion_equipo = models.CharField(max_length=50, choices=UBICACION_CHOICES)
    ubicacion_otro = models.CharField(max_length=100, blank=True)
    motivo_servicio = models.TextField()
    solucion_realizada = models.TextField()
    observaciones = models.TextField(blank=True)
    recomendaciones = models.TextField(blank=True)
    valor_servicio = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, blank=True)
    firma_cliente = models.ImageField(upload_to='firmas/', blank=True, null=True)
    firma_base64 = models.TextField(blank=True, null=True, help_text='Firma en formato base64')
    inicio_desplazamiento = models.DateTimeField(null=True, blank=True)
    duracion_desplazamiento = models.CharField(max_length=50, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'visita_reporte'
        verbose_name = 'Reporte de Visita'
        verbose_name_plural = 'Reportes de Visita'

    def __str__(self):
        return f"Reporte #{self.visita.numero_tarea}"


class EvidenciaFotografica(models.Model):
    visita = models.ForeignKey(
        VisitaTecnica,
        on_delete=models.CASCADE,
        related_name='evidencias',
    )
    imagen = models.ImageField(upload_to='evidencias/')
    descripcion = models.CharField(max_length=200, blank=True)
    orden = models.IntegerField(default=0)
    subida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visita_evidencia'
        verbose_name = 'Evidencia Fotográfica'
        verbose_name_plural = 'Evidencias Fotográficas'
        ordering = ['orden', 'subida_en']

    def __str__(self):
        return f"Evidencia #{self.pk} — Visita #{self.visita.numero_tarea}"
