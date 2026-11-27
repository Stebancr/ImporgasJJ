from django.conf import settings
from usuarios.models import Credenciales, Usuario
from ecommerce.models import Brand, Category, Product
assert settings.DEBUG and settings.DATABASES['default']['NAME'] == 'security_qa'
profile, _ = Usuario.objects.get_or_create(cedula='security-browser-fixture', defaults={'nombre_completo': 'Synthetic QA', 'correo': 'qa@example.invalid'})
user, _ = Credenciales.objects.get_or_create(usuario='security-browser-fixture', defaults={'usuario_rel': profile, 'tipo_usuario': 4, 'estado': 1})
user.set_password('Synthetic@Browser937!')
user.save(update_fields=['password'])
brand, _ = Brand.objects.get_or_create(name='Marca prueba sesión')
category, _ = Category.objects.get_or_create(name='Categoría prueba sesión')
Product.objects.get_or_create(name='Producto prueba sesión', defaults={
    'brand': brand, 'category': category, 'price': 100000,
})
print('ISOLATED_BROWSER_USER_READY')
