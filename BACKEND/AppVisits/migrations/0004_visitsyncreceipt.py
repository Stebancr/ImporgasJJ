from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('AppVisits', '0003_task_number_and_completion_email')]
    operations = [
        migrations.CreateModel(
            name='VisitSyncReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operation_key', models.CharField(max_length=100)),
                ('request_hash', models.CharField(max_length=64)),
                ('response_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='usuarios.credenciales')),
                ('visita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sync_receipts', to='AppVisits.visitatecnica')),
            ],
            options={'db_table': 'visita_sync_receipt', 'constraints': [models.UniqueConstraint(fields=('visita', 'usuario', 'operation_key'), name='unique_visit_sync_operation')]},
        ),
    ]
