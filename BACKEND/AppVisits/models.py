from django.db import models
from django.db.models import Q


class ClienteVisita(models.Model):
    """Información del cliente para una visita técnica."""
    nombre = models.CharField(max_length=200)
    identificacion = models.CharField(max_length=30, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.CharField(max_length=100, blank=True)
    direccion = models.TextField()
    indicaciones_llegada = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visita_cliente'
        verbose_name = 'Cliente de Visita'
        verbose_name_plural = 'Clientes de Visita'

    def __str__(self):
        return f"{self.nombre}"


class TipoVisita(models.Model):
    codigo = models.SlugField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visita_tipo'
        ordering = ['nombre', 'codigo']

    def __str__(self):
        return self.nombre


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
        ('visita_urbana', 'VISITA TECNICA PERIMETRO URBANO'),
        ('instalacion_calentador', '2025 INSTALACION DE CALENTADOR'),
        ('mantenimiento_calentador', '2025 MANTENIMIENTO O REPARACION DE CALENTADOR'),
        ('instalacion_secadora', '2025 INSTALACION DE SECADORA'),
        ('servicio_cancelado', 'SERVICIO CANCELADO'),
        ('visita_afueras', 'VISITA TECNICA PERIMETRO URBANO AFUERAS'),
        ('mantenimiento_estufa', '2025 MANTENIMIENTO O REPARACION DE ESTUFA'),
        ('revision_periodica', 'REVISION PERIODICA'),
        ('mantenimiento_acumulacion', '2025 MANTENIMIENTO O REPARACION CALENTADOR DE ACUMULACION A GAS'),
        ('programacion_doble', 'PROGRAMACION DOBLE'),
        ('mantenimiento_turco', '2025 MANTENIMIENTO O REPARACION CALENTADOR DE TURCO DE PASO'),
    ]

    numero_tarea = models.CharField(max_length=20, unique=True, blank=True, null=True, editable=False)
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
    tipo_tarea = models.CharField(max_length=50)
    tipo_tarea_etiqueta = models.CharField(max_length=150, blank=True)
    fecha = models.DateField()
    hora = models.TimeField()
    descripcion = models.TextField(blank=True)
    observaciones_iniciales = models.TextField(blank=True)
    valor_visita = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor monetario acordado para la visita técnica.',
    )
    costo_inicial = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    creado_por = models.ForeignKey(
        'usuarios.Credenciales',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visitas_creadas',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    correo_completada_en = models.DateTimeField(null=True, blank=True, editable=False)
    correo_completada_error = models.TextField(blank=True, editable=False)
    pdf_final = models.FileField(upload_to='visitas_pdf/', blank=True, null=True)
    pdf_sha256 = models.CharField(max_length=64, blank=True, default='')
    pdf_source_hash = models.CharField(max_length=64, blank=True, default='')
    pdf_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    pdf_generado_en = models.DateTimeField(null=True, blank=True)
    pdf_estado = models.CharField(max_length=20, blank=True, default='')
    pdf_error = models.CharField(max_length=300, blank=True, default='')
    pdf_link_version = models.PositiveIntegerField(default=1)
    whatsapp_notificacion_estado = models.CharField(max_length=20, blank=True, default='')
    whatsapp_notificacion_error = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        db_table = 'visita_tecnica'
        verbose_name = 'Visita Técnica'
        verbose_name_plural = 'Visitas Técnicas'
        ordering = ['fecha', 'hora']
        constraints = [
            models.CheckConstraint(
                condition=Q(valor_visita__gte=0) | Q(valor_visita__isnull=True),
                name='visita_valor_no_negativo',
            ),
            models.CheckConstraint(
                condition=Q(costo_inicial__gte=0) | Q(costo_inicial__isnull=True),
                name='visita_costo_inicial_no_negativo',
            ),
        ]

    def __str__(self):
        return f"#{self.numero_tarea} — {self.cliente.nombre} ({self.get_estado_display()})"

    def get_tipo_tarea_display(self):
        # La etiqueta se congela al crear la visita: editar un tipo no cambia
        # el significado de los informes históricos.
        return self.tipo_tarea_etiqueta or dict(self.TIPO_TAREA_CHOICES).get(self.tipo_tarea, self.tipo_tarea)

    def save(self, *args, **kwargs):
        if self.pk:
            self.numero_tarea = str(999 + self.pk)
            return super().save(*args, **kwargs)
        self.numero_tarea = None
        super().save(*args, **kwargs)
        self.numero_tarea = str(999 + self.pk)
        type(self).objects.filter(pk=self.pk).update(numero_tarea=self.numero_tarea)


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
    archivada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'visita_evidencia'
        verbose_name = 'Evidencia Fotográfica'
        verbose_name_plural = 'Evidencias Fotográficas'
        ordering = ['orden', 'subida_en']

    def __str__(self):
        return f"Evidencia #{self.pk} — Visita #{self.visita.numero_tarea}"


class VisitSyncReceipt(models.Model):
    """Durable receipt for replaying a completed offline operation safely."""
    visita = models.ForeignKey(VisitaTecnica, on_delete=models.CASCADE, related_name='sync_receipts')
    usuario = models.ForeignKey('usuarios.Credenciales', on_delete=models.PROTECT)
    operation_key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)
    response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visita_sync_receipt'
        constraints = [models.UniqueConstraint(fields=('visita', 'usuario', 'operation_key'), name='unique_visit_sync_operation')]


class CambioCostoVisita(models.Model):
    visita = models.ForeignKey(VisitaTecnica, on_delete=models.CASCADE, related_name='cambios_costo')
    usuario = models.ForeignKey('usuarios.Credenciales', null=True, on_delete=models.SET_NULL)
    valor_anterior = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_nuevo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    motivo = models.TextField(blank=True)
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visita_cambio_costo'
        ordering = ['-cambiado_en']
