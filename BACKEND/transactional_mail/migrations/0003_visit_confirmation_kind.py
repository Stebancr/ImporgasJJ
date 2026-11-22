from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('transactional_mail', '0002_delivery_max_attempts_alter_delivery_state')]
    operations = [migrations.AlterField(
        model_name='delivery', name='kind',
        field=models.CharField(max_length=20, choices=[
            ('order', 'Compra aprobada'), ('visit', 'Visita finalizada'),
            ('visit_confirmation', 'Visita programada'),
        ]),
    )]
