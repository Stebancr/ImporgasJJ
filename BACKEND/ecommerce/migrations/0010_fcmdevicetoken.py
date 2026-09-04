from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ecommerce', '0009_order_wompi_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='FCMDeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=4096, unique=True, verbose_name='Token FCM')),
                ('platform', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web'), ('unknown', 'Desconocida')], default='unknown', max_length=10, verbose_name='Plataforma')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('last_error', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fcm_device_tokens', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={'db_table': 'fcm_device_tokens', 'ordering': ['-updated_at']},
        ),
        migrations.AddIndex(
            model_name='fcmdevicetoken',
            index=models.Index(fields=['user', 'is_active'], name='fcm_user_active_idx'),
        ),
    ]
