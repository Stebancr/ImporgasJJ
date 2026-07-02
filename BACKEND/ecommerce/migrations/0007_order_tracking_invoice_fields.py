"""
Migration: add UUID tracking code, order_number, customer info,
           accounting fields, and Wompi payment fields to Order.

Uses a two-step approach for the unique UUID field (Django best practice):
  Step 1 – Add tracking_code as nullable, populate existing rows, then make it unique.
  Step 2 – Add all remaining new fields with their defaults.
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_tracking_codes(apps, schema_editor):
    """Assign a unique UUID to every existing order that has none."""
    Order = apps.get_model('ecommerce', 'Order')
    for order in Order.objects.filter(tracking_code__isnull=True):
        order.tracking_code = uuid.uuid4()
        order.save(update_fields=['tracking_code'])


def populate_order_numbers(apps, schema_editor):
    """Assign ORD-XXXXX numbers to existing orders."""
    Order = apps.get_model('ecommerce', 'Order')
    for order in Order.objects.filter(order_number='').order_by('id'):
        order.order_number = f"ORD-{order.id:05d}"
        order.save(update_fields=['order_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0006_allow_negative_stock_and_charfield_correo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Step 1: tracking_code (UUID, unique) ──────────────────────────────
        migrations.AddField(
            model_name='order',
            name='tracking_code',
            field=models.UUIDField(null=True, blank=True, verbose_name='Código de seguimiento (UUID)'),
        ),
        migrations.RunPython(populate_tracking_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='tracking_code',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Código de seguimiento (UUID)'),
        ),

        # ── Step 2: order_number ──────────────────────────────────────────────
        migrations.AddField(
            model_name='order',
            name='order_number',
            field=models.CharField(max_length=20, default='', editable=False, verbose_name='Número de orden (ORD-XXXXX)'),
        ),
        migrations.RunPython(populate_order_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='order_number',
            field=models.CharField(max_length=20, unique=True, default='', editable=False, verbose_name='Número de orden (ORD-XXXXX)'),
        ),

        # ── Step 3: customer fields ───────────────────────────────────────────
        migrations.AddField(
            model_name='order',
            name='customer_name',
            field=models.CharField(max_length=200, default='', verbose_name='Nombre del cliente'),
        ),
        migrations.AddField(
            model_name='order',
            name='customer_email',
            field=models.EmailField(default='', verbose_name='Correo del cliente'),
        ),
        migrations.AddField(
            model_name='order',
            name='customer_phone',
            field=models.CharField(max_length=30, blank=True, default='', verbose_name='Teléfono del cliente'),
        ),

        # ── Step 4: shipping fields ───────────────────────────────────────────
        migrations.AlterField(
            model_name='order',
            name='shipping_address',
            field=models.TextField(default='', verbose_name='Dirección de envío'),
        ),
        migrations.AddField(
            model_name='order',
            name='city',
            field=models.CharField(max_length=100, blank=True, default='', verbose_name='Ciudad'),
        ),
        migrations.AddField(
            model_name='order',
            name='department',
            field=models.CharField(max_length=100, blank=True, default='', verbose_name='Departamento'),
        ),
        migrations.AddField(
            model_name='order',
            name='postal_code',
            field=models.CharField(max_length=20, blank=True, default='', verbose_name='Código postal'),
        ),

        # ── Step 5: accounting fields ─────────────────────────────────────────
        migrations.AddField(
            model_name='order',
            name='subtotal',
            field=models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Subtotal'),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_cost',
            field=models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo de envío'),
        ),

        # ── Step 6: payment fields ────────────────────────────────────────────
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                max_length=20,
                choices=[('wompi', 'Wompi (tarjeta/PSE/Nequi)'), ('cash', 'Contra entrega')],
                default='cash',
                verbose_name='Método de pago',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='wompi_transaction_id',
            field=models.CharField(max_length=200, blank=True, default='', verbose_name='ID de transacción Wompi'),
        ),
        migrations.AddField(
            model_name='order',
            name='wompi_reference',
            field=models.CharField(max_length=200, blank=True, default='', verbose_name='Referencia Wompi'),
        ),

        # ── Step 7: status — add 'cancelled' choice & notes ───────────────────
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                max_length=15,
                choices=[
                    ('pending',   'Pendiente'),
                    ('paid',      'Pagado'),
                    ('preparing', 'En preparación'),
                    ('shipping',  'En camino'),
                    ('delivered', 'Entregado'),
                    ('installed', 'Instalado'),
                    ('cancelled', 'Cancelado'),
                ],
                default='pending',
                verbose_name='Estado',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='notes',
            field=models.TextField(blank=True, default='', verbose_name='Notas del pedido'),
        ),

        # ── Step 8: user FK → nullable (allow guest checkout) ─────────────────
        migrations.AlterField(
            model_name='order',
            name='user',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orders',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Usuario registrado',
            ),
        ),
    ]
