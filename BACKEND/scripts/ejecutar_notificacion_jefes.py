#!/usr/bin/env python
"""
Script para ejecutar la tarea notificar_jefes_por_colaboradores_sin_progreso
y verificar que funciona correctamente.

Ejecución:
  python manage.py shell
  >>> exec(open('scripts/ejecutar_notificacion_jefes.py').read())
"""

from notificaciones.tasks import notificar_jefes_por_colaboradores_sin_progreso
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('notificaciones')

print("\n" + "="*80)
print("🚀 EJECUTANDO: notificar_jefes_por_colaboradores_sin_progreso")
print("="*80)
print(f"\n⏰ Horario: Cada lunes a las 18:00")
print(f"📋 Descripción: Notificar a jefes sobre el estado de capacitaciones")
print(f"\n")

try:
    print("📤 Iniciando tarea...\n")
    resultado = notificar_jefes_por_colaboradores_sin_progreso()
    print("\n✅ Tarea ejecutada exitosamente")
    print(f"Resultado: {resultado}")
except Exception as e:
    print(f"\n❌ Error al ejecutar la tarea:")
    print(f"   {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ EJECUCIÓN COMPLETADA")
print("="*80 + "\n")
