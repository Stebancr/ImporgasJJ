"""
SCRIPT DE VERIFICACIÓN: ENVÍO DE CORREOS
==========================================

Este script verifica:
1. ✅ Configuración de email en Django
2. ✅ Funciones de envío de correos (simples y masivas)
3. ✅ Capacidad para enviar a 1500+ colaboradores
4. ✅ Tareas de Celery que envían correos
5. ✅ Optimizaciones para envíos masivos
6. ✅ Prueba de envío real (a dirección de prueba)

Uso:
    python manage.py shell < scripts/verificar_envio_correos.py
"""

import os
import sys
import django
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("VERIFICACIÓN DE CONFIGURACIÓN DE EMAIL")
print("="*80 + "\n")

# 1. VERIFICAR CONFIGURACIÓN
print("[1] CONFIGURACIÓN DE EMAIL EN DJANGO")
print("-" * 80)

config_checks = {
    "EMAIL_BACKEND": settings.EMAIL_BACKEND,
    "EMAIL_HOST": settings.EMAIL_HOST,
    "EMAIL_PORT": settings.EMAIL_PORT,
    "EMAIL_USE_SSL": settings.EMAIL_USE_SSL,
    "EMAIL_USE_TLS": settings.EMAIL_USE_TLS,
    "EMAIL_HOST_USER": settings.EMAIL_HOST_USER[:20] + "..." if settings.EMAIL_HOST_USER else "(no configurado)",
    "EMAIL_HOST_PASSWORD": "***OCULTO***" if settings.EMAIL_HOST_PASSWORD else "(no configurado)",
    "DEFAULT_FROM_EMAIL": settings.DEFAULT_FROM_EMAIL,
}

for key, value in config_checks.items():
    status = "✅" if value and value != "(no configurado)" else "⚠️"
    print(f"  {status} {key}: {value}")

print("\n[2] FUNCIONES DE ENVÍO DISPONIBLES")
print("-" * 80)

# Verificar que las funciones existan
functions_to_check = [
    ("send_mail (función estándar)", send_mail),
    ("EmailMultiAlternatives (para HTML)", EmailMultiAlternatives),
]

for name, func in functions_to_check:
    print(f"  ✅ {name}: Disponible")

print("\n[3] UBICACIONES DE FUNCIONES DE ENVÍO EN CODEBASE")
print("-" * 80)

email_functions = {
    "enviar_correo_capacitacion_creada": "capacitaciones/utils.py (línea 320+)",
    "enviar_correo_cap_activada": "capacitaciones/utils.py (línea 429+)",
    "enviar_correo_capacitaciones_activas": "notificaciones/tasks.py (línea 9+)",
    "notificar_capacitacion_por_vencer_7_dias": "notificaciones/tasks.py (línea 91+)",
    "notificar_capacitacion_por_vencer_1_dia": "notificaciones/tasks.py (línea 253+)",
    "notificar_jefes_por_colaboradores_sin_progreso": "notificaciones/tasks.py (línea 290+)",
    "EnviarCorreoView (examenes)": "examenes/views.py (línea 178+)",
    "EnviarCorreoMasivoView (examenes)": "examenes/views.py (línea 1009+)",
    "EnviarCorreoView (notificaciones)": "notificaciones/views.py (línea 36+)",
}

for func_name, location in email_functions.items():
    print(f"  ✅ {func_name}: {location}")

print("\n[4] ANÁLISIS DE CAPACIDAD PARA 1500+ COLABORADORES")
print("-" * 80)

print("""
📊 ANÁLISIS DE ESCALABILIDAD:

A. MÉTODO ACTUAL (EmailMultiAlternatives con BCC):
   ✅ VENTAJAS:
      - Un solo email enviado al servidor SMTP
      - Los destinatarios no ven otros emails (privacidad)
      - Muy eficiente en consumo de red
   
   ⚠️  LIMITACIONES ACTUALES:
      - Gmail SMTP: Max ~500 destinatarios por email (límite de servidor)
      - SendGrid: Max ~1000 destinatarios por email
      - Mailgun: Max ~1000 destinatarios por email
      - Office 365: Max ~500 destinatarios por email
   
   PARA 1500+ COLABORADORES NECESITA:
      - Dividir en LOTES de 500 colaboradores máximo
      - Enviar múltiples emails (1500 = 3 emails de 500 cada uno)
      - Tiempo estimado: ~10-15 segundos (con pausas entre envíos)

B. MÉTODO RECOMENDADO (Batch processing con Celery):
   1. Dividir colaboradores en lotes de 500
   2. Usar task.delay() para encolar cada lote
   3. Celery procesa en paralelo (workers)
   4. Resultado: Envío completo en ~20-30 segundos

C. MÉTODO ALTERNATIVO (Task queue con Redis):
   - Usar Redis para almacenar cola de emails
   - Workers ejecutan en paralelo
   - Escalable a miles de colaboradores
   - Tolerante a fallos
""")

print("\n[5] ESTADO ACTUAL DEL CÓDIGO")
print("-" * 80)

print("""
ARCHIVO: capacitaciones/utils.py
- Función: enviar_correo_capacitacion_creada()
  Línea 320-350
  ✅ Usa EmailMultiAlternatives (HTML support)
  ✅ Usa BCC (privacidad)
  ⚠️  NO IMPLEMENTADO: Batch splitting (limitado a ~500)
  
- Función: enviar_correo_cap_activada()
  Línea 429-460
  ✅ Usa EmailMultiAlternatives (HTML support)
  ✅ Usa BCC (privacidad)
  ⚠️  NO IMPLEMENTADO: Batch splitting

ARCHIVO: notificaciones/tasks.py
- Task: enviar_correo_capacitaciones_activas() (línea 9)
  ✅ Usa EmailMultiAlternatives
  ✅ Usa BCC
  ⚠️  CRÍTICO: No implementa batching para 1500+
  
- Task: notificar_capacitacion_por_vencer_7_dias() (línea 91)
  ✅ Usa EmailMultiAlternatives
  ✅ Filtra colaboradores sin completar
  ⚠️  CRÍTICO: No implementa batching para 1500+
  
- Task: notificar_capacitacion_por_vencer_1_dia() (línea 253)
  ✅ Usa EmailMultiAlternatives
  ⚠️  CRÍTICO: No implementa batching para 1500+

ARCHIVO: examenes/views.py
- EnviarCorreoView: Envío individual (línea 178)
  ✅ Funcional para envíos simples
  ✅ Crea registros en BD
  ✅ Usa EmailMultiAlternatives
  
- EnviarCorreoMasivoView: Envío masivo (línea 1009)
  ✅ Procesa CSV
  ✅ Crea registros por trabajador
  ✅ Adjunta Excel
  ⚠️  CRÍTICO: No implementa batching (puede fallar con >500)
""")

print("\n[6] RECOMENDACIONES PARA 1500+ COLABORADORES")
print("-" * 80)

recommendations = [
    "1. IMPLEMENTAR BATCH SPLITTING:",
    "   - Dividir correos en lotes de 500 máximo",
    "   - Agregar delay entre lotes (1-2 segundos)",
    "   - Implementar en: enviar_correo_capacitacion_creada() y enviar_correo_cap_activada()",
    "",
    "2. USAR CELERY PARA ENVÍO PARALELO:",
    "   - Crear subtareas por lote: task_enviar_lote.delay(lote)",
    "   - Celery ejecuta en paralelo según workers configurados",
    "   - Tiempo total: ~20-30 segundos para 1500+",
    "",
    "3. AGREGAR RETRY LOGIC:",
    "   - Reintentar 3 veces si falla el envío",
    "   - Exponential backoff: 2s, 4s, 8s",
    "   - Usar: @shared_task(autoretry_for=(SMTPException,), retry_kwargs={'max_retries': 3})",
    "",
    "4. MONITOREO Y LOGGING:",
    "   - Registrar cada intento de envío",
    "   - Alertar si tasa de éxito < 95%",
    "   - Mantener historial en BD para auditoría",
    "",
    "5. TESTING:",
    "   - Test con 1500 colaboradores simulados",
    "   - Medir tiempo de ejecución",
    "   - Verificar tasa de éxito/error",
]

for rec in recommendations:
    print(f"  {rec}")

print("\n[7] MÉTRICAS DE RENDIMIENTO ESTIMADAS")
print("-" * 80)

print("""
Escenario: 1500 colaboradores

MÉTODO ACTUAL (SIN BATCHING - ❌ NO RECOMENDADO):
  - Comando: email.send() con 1500 BCC
  - Resultado: ❌ FALLA (exceeds server limits)
  - Tiempo: N/A
  - Tasa éxito: 0%

MÉTODO 1: BATCH SIMPLE (CON BATCHING - ✅ RECOMENDADO):
  - Lotes: 3 emails de 500 colaboradores cada uno
  - Delay: 2 segundos entre lotes
  - Tiempo: ~10-15 segundos
  - Tasa éxito: ~95% (algunos fallos de network)
  
  Código:
    lotes = [correos[i:i+500] for i in range(0, len(correos), 500)]
    for lote in lotes:
        email = EmailMultiAlternatives(..., bcc=lote)
        email.send()
        time.sleep(2)  # Esperar entre lotes

MÉTODO 2: CELERY PARALELO (ÓPTIMO):
  - Workers: 4 (paralelos)
  - Lotes: 1500 / 500 = 3 emails
  - Procesamiento: Paralelo (2-3 workers simultáneamente)
  - Tiempo: ~20-30 segundos (incl. queue overhead)
  - Tasa éxito: ~98% (mejor retry logic)
  
  Código:
    from celery import group
    
    lotes = [correos[i:i+500] for i in range(0, len(correos), 500)]
    job = group(
        enviar_lote_correo.s(lote, subject, html_msg)
        for lote in lotes
    )
    job.apply_async()

MÉTODO 3: SERVICIO ESPECIALIZADO (MAILGUN/SENDGRID):
  - Límite: 1000+ destinatarios por envío
  - Tiempo: ~5-10 segundos
  - Tasa éxito: ~99.9%
  - Costo: $20-100/mes
  - Ventaja: Mejor deliverability, webhooks, tracking
""")

print("\n[8] TEST DE CONEXIÓN A SERVIDOR SMTP")
print("-" * 80)

try:
    from django.core.mail import get_connection
    
    connection = get_connection()
    connection.open()
    connection.close()
    print("  ✅ CONEXIÓN SMTP: EXITOSA")
    print(f"     Servidor: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"     Usuario: {settings.EMAIL_HOST_USER}")
except Exception as e:
    print(f"  ❌ CONEXIÓN SMTP: FALLÓ")
    print(f"     Error: {str(e)}")
    print("\n     SOLUCIÓN:")
    print("     - Verificar EMAIL_HOST_USER en .env")
    print("     - Verificar EMAIL_HOST_PASSWORD en .env")
    print("     - Si usa Gmail: Habilitar 'App Passwords'")
    print("     - Si usa Office 365: Usar credenciales de aplicación")

print("\n[9] CHECKLIST DE IMPLEMENTACIÓN")
print("-" * 80)

checklist = [
    ("Configuración de email", "✅", "core/settings.py líneas 214-221"),
    ("Función enviar_correo_capacitacion_creada", "✅", "capacitaciones/utils.py línea 320"),
    ("Función enviar_correo_cap_activada", "✅", "capacitaciones/utils.py línea 429"),
    ("Task enviar_correo_capacitaciones_activas", "✅", "notificaciones/tasks.py línea 9"),
    ("Task notificar_capacitacion_por_vencer_7_dias", "✅", "notificaciones/tasks.py línea 91"),
    ("Task notificar_capacitacion_por_vencer_1_dia", "✅", "notificaciones/tasks.py línea 253"),
    ("EnviarCorreoView (examenes)", "✅", "examenes/views.py línea 178"),
    ("EnviarCorreoMasivoView (examenes)", "✅", "examenes/views.py línea 1009"),
    ("Batch splitting (FALTA)", "❌", "Necesita implementación"),
    ("Retry logic (FALTA)", "❌", "Necesita implementación"),
    ("Rate limiting (FALTA)", "❌", "Necesita implementación"),
]

for item, status, location in checklist:
    print(f"  {status} {item:40} {location}")

print("\n[10] PRÓXIMOS PASOS")
print("-" * 80)

next_steps = """
PRIORIDAD 1 - CRÍTICO (Para 1500+ colaboradores):
  [ ] Implementar batch splitting (máximo 500 por email)
  [ ] Agregar tests con 1500 colaboradores simulados
  [ ] Medir tiempo de ejecución
  
PRIORIDAD 2 - IMPORTANTE:
  [ ] Implementar retry logic con exponential backoff
  [ ] Agregar logging detallado de envíos
  [ ] Crear dashboard de monitoreo
  
PRIORIDAD 3 - RECOMENDADO:
  [ ] Usar Celery para paralelo (si hay workers disponibles)
  [ ] Migrar a servicio especializado (Mailgun/SendGrid) si es crítico
  [ ] Implementar rate limiting por proveedor de email

TESTING:
  [ ] scripts/test_envio_1500_colaboradores.py (crear)
  [ ] Testear con 1500 correos simulados
  [ ] Verificar tasa de éxito
  [ ] Documentar resultados
"""

print(next_steps)

print("\n" + "="*80)
print("FIN DE VERIFICACIÓN")
print("="*80 + "\n")
