from django.contrib import admin
from .models import Cotizacion, CotizacionItem, Factura, FacturaItem


class CotizacionItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'location', 'cliente_nombre', 'estado', 'total', 'fecha_emision']
    list_filter = ['estado', 'location']
    search_fields = ['numero', 'cliente_nombre', 'cliente_cedula']
    readonly_fields = ['numero', 'subtotal', 'descuento_monto', 'impuesto_monto', 'total']
    inlines = [CotizacionItemInline]


class FacturaItemInline(admin.TabularInline):
    model = FacturaItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'location', 'cliente_nombre', 'estado', 'total', 'fecha_emision']
    list_filter = ['estado', 'location']
    search_fields = ['numero', 'cliente_nombre', 'cliente_cedula']
    readonly_fields = ['numero', 'subtotal', 'descuento_monto', 'impuesto_monto', 'total']
    inlines = [FacturaItemInline]
