import django
import json
from django.conf import settings

django.setup()
from rest_framework.test import APIRequestFactory
from analitica.views import ProgresoEmpresarialView

factory = APIRequestFactory()
request = factory.get('/analitica/progreso/')
response = ProgresoEmpresarialView.as_view()(request)

try:
    data = response.data
except Exception:
    # Fallback: render to JSON if needed
    from rest_framework.renderers import JSONRenderer
    renderer = JSONRenderer()
    rendered = renderer.render(response.data)
    print(rendered.decode('utf-8')[:2000])
else:
    print(json.dumps(data, ensure_ascii=False)[:2000])
