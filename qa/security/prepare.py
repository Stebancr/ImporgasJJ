from django.conf import settings
from usuarios.models import Credenciales, Usuario
assert settings.DEBUG and settings.DATABASES['default']['NAME'] == 'security_qa'
profile, _ = Usuario.objects.get_or_create(cedula='security-browser-fixture', defaults={'nombre_completo': 'Synthetic QA', 'correo': 'qa@example.invalid'})
user, _ = Credenciales.objects.get_or_create(usuario='security-browser-fixture', defaults={'usuario_rel': profile, 'tipo_usuario': 4, 'estado': 1})
user.set_password('Synthetic@Browser937!')
user.save(update_fields=['password'])
print('ISOLATED_BROWSER_USER_READY')
