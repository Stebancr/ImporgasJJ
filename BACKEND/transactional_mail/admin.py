from django.contrib import admin
from django.utils import timezone
from django.db.models import F
from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display=('id','kind','object_id','recipient','state','attempts','sent_at','last_error')
    list_filter=('kind','state')
    readonly_fields=tuple(field.name for field in Delivery._meta.fields)
    actions=['retry_failed']

    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

    @admin.action(description='Reintentar fallidos (excluye entregas inciertas y enviadas)')
    def retry_failed(self,request,queryset):
        queryset.filter(state='failed').update(state='pending',max_attempts=F('attempts')+3,next_attempt_at=timezone.now())
