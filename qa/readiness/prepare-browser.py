import json, uuid
from pathlib import Path
from django.conf import settings
from usuarios.models import Credenciales, Usuario
from rest_framework_simplejwt.tokens import AccessToken
assert settings.DEBUG and settings.CRM_TEST_MODE and not settings.CRM_EXTERNAL_SEND_ENABLED
assert settings.DATABASES['default']['NAME']=='crm_audit'
profile=Usuario.objects.create(cedula='qa-'+uuid.uuid4().hex[:12],nombre_completo='Administrador QA',correo='qa@example.invalid')
user=Credenciales.objects.create(usuario='readiness-admin-'+uuid.uuid4().hex,tipo_usuario=4,estado=1,usuario_rel=profile)
user.set_unusable_password();user.save(update_fields=['password'])
Path('/tmp/readiness-auth.json').write_text(json.dumps({'token':str(AccessToken.for_user(user)),'user_id':user.pk}))
print('ISOLATED_ADMIN_READY')
