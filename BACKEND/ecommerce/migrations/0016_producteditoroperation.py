from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def normalize_primary(apps, schema_editor):
    Image = apps.get_model('ecommerce', 'ProductImage')
    for product_id in Image.objects.values_list('product_id', flat=True).distinct():
        images = Image.objects.filter(product_id=product_id)
        selected = images.filter(is_primary=True).order_by('order', 'id').first() or images.order_by('order', 'id').first()
        images.exclude(pk=selected.pk).update(is_primary=False)
        images.filter(pk=selected.pk).update(is_primary=True)


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0015_order_discounts_order_paid_total_order_taxes_and_more'),
                    migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='ProductEditorOperation', fields=[
        ('key', models.UUIDField(primary_key=True, serialize=False)),
        ('fingerprint', models.CharField(max_length=64)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ecommerce.product')),
    ]), migrations.RunPython(normalize_primary, migrations.RunPython.noop),
        migrations.AddConstraint(model_name='productimage', constraint=models.UniqueConstraint(
            fields=('product',), condition=models.Q(is_primary=True), name='uniq_product_primary_image'))]
