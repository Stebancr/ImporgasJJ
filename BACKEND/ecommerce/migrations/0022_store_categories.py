from django.db import migrations
from django.utils.text import slugify


CATEGORIES = (
    ('Electricidad', 'electricidad', 'zap', ('electricidades',)),
    ('Medidor de gas', 'medidor-de-gas', 'meter', ('medidores-de-gas',)),
    ('Manómetro', 'manometro', 'gauge', ('manometros',)),
    ('Regulador de gas', 'regulador-de-gas', 'sliders', ('reguladores-de-gas',)),
    ('Latón', 'laton', 'link', ('latones',)),
    ('Galvanizado', 'galvanizado', 'construction', ('galvanizados',)),
    ('Tanque de acumulación', 'tanque-de-acumulacion', 'cylinder', ('tanques-de-acumulacion',)),
)


def add_categories(apps, schema_editor):
    categories = apps.get_model('ecommerce', 'Category').objects.using(schema_editor.connection.alias)
    existing = list(categories.values_list('name', 'slug', 'order'))
    order = max((row[2] for row in existing), default=-1)
    for name, slug, icon, aliases in CATEGORIES:
        equivalent = {slug, *aliases}
        if any(slugify(old_name) in equivalent or old_slug in equivalent
               for old_name, old_slug, _ in existing):
            continue
        order = min(order + 1, 32767)
        categories.get_or_create(slug=slug, defaults={'name': name, 'icon': icon, 'order': order})


class Migration(migrations.Migration):
    dependencies = [('ecommerce', '0021_rollback_write_defaults')]
    # Categories may have acquired product relations. Keep them on rollback.
    operations = [migrations.RunPython(add_categories, migrations.RunPython.noop)]
