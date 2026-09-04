from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0008_alter_order_department_alter_order_notes_and_more')]

    operations = [
        migrations.AddField(
            model_name='order',
            name='wompi_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PENDING', 'Pendiente'), ('APPROVED', 'Aprobado'),
                    ('DECLINED', 'Rechazado'), ('VOIDED', 'Anulado'), ('ERROR', 'Error'),
                ],
                max_length=10,
                verbose_name='Estado de pago Wompi',
            ),
        ),
    ]
