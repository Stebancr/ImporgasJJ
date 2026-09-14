import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0011_order_payment_confirmation_email')]
    operations = [
        migrations.CreateModel(
            name='WompiPaymentIntent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tracking_code', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('reference', models.CharField(max_length=200, unique=True)),
                ('transaction_id', models.CharField(blank=True, max_length=200, null=True, unique=True)),
                ('wompi_status', models.CharField(choices=[('PENDING', 'Pendiente'), ('APPROVED', 'Aprobado'), ('DECLINED', 'Rechazado'), ('VOIDED', 'Anulado'), ('ERROR', 'Error')], default='PENDING', max_length=10)),
                ('checkout_data', models.JSONField(default=dict)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=14)),
                ('shipping_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, max_digits=14)),
                ('currency', models.CharField(default='COP', max_length=3)),
                ('provider_payload', models.JSONField(blank=True, default=dict)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_intent', to='ecommerce.order')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'wompi_payment_intents', 'ordering': ['-created_at']},
        ),
    ]
