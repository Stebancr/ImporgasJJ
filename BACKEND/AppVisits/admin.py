from django.contrib import admin
from .models import ClienteVisita, VisitaTecnica, ReporteVisita, EvidenciaFotografica


@admin.register(ClienteVisita)
class ClienteVisitaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'identificacion', 'telefono', 'correo', 'direccion']
    search_fields = ['nombre', 'identificacion', 'correo']


class EvidenciaInline(admin.TabularInline):
    model = EvidenciaFotografica
    extra = 0
    readonly_fields = ['subida_en']


class ReporteInline(admin.StackedInline):
    model = ReporteVisita
    extra = 0
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(VisitaTecnica)
class VisitaTecnicaAdmin(admin.ModelAdmin):
    list_display = ['numero_tarea', 'cliente', 'tecnico', 'tipo_tarea', 'fecha', 'hora', 'estado']
    list_filter = ['estado', 'tipo_tarea', 'fecha']
    search_fields = ['numero_tarea', 'cliente__nombre', 'tecnico__usuario']
    inlines = [ReporteInline, EvidenciaInline]
    readonly_fields = ['numero_tarea', 'fecha_creacion', 'fecha_actualizacion']


@admin.register(ReporteVisita)
class ReporteVisitaAdmin(admin.ModelAdmin):
    list_display = ['visita', 'persona_atiende', 'equipo', 'valor_servicio', 'metodo_pago']
    search_fields = ['visita__numero_tarea', 'persona_atiende']


@admin.register(EvidenciaFotografica)
class EvidenciaFotograficaAdmin(admin.ModelAdmin):
    list_display = ['visita', 'orden', 'subida_en']
