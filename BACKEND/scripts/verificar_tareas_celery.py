#!/usr/bin/env python
"""
Script para verificar el funcionamiento de todas las tareas automatizadas de Celery.
Ejecutar: python manage.py shell < scripts/verificar_tareas_celery.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from celery import current_app
from notificaciones.tasks import (
    enviar_correo_capacitaciones_activas_y_activar,
    notificar_capacitacion_por_vencer_7_dias,
    notificar_capacitacion_por_vencer_1_dia,
    desactivar_capacitaciones,
    notificar_jefes_por_colaboradores_sin_progreso
)

def verificar_tareas():
    """Verifica que todas las tareas de Celery estén registradas y sean ejecutables"""
    
    print("=" * 80)
    print("VERIFICACIÓN DE TAREAS AUTOMATIZADAS (CELERY)")
    print("=" * 80)
    print()
    
    # 1. Verificar configuración de Celery
    print("1️⃣ VERIFICANDO CONFIGURACIÓN DE CELERY")
    print("-" * 80)
    
    beat_schedule = current_app.conf.beat_schedule
    print(f"✅ Celery Beat Schedule configurado con {len(beat_schedule)} tareas")
    print()
    
    # 2. Listar todas las tareas programadas
    print("2️⃣ TAREAS PROGRAMADAS EN CELERY BEAT")
    print("-" * 80)
    
    for nombre, config in beat_schedule.items():
        print(f"\n📅 Tarea: {nombre}")
        print(f"   └─ Task: {config.get('task', 'N/A')}")
        print(f"   └─ Schedule: {config.get('schedule', 'N/A')}")
    
    print()
    
    # 3. Verificar tareas registradas
    print("3️⃣ VERIFICANDO TAREAS REGISTRADAS")
    print("-" * 80)
    
    tareas_notificaciones = [
        ('notificaciones.tasks.enviar_correo_capacitaciones_activas_y_activar', 'Enviar correos y activar capacitaciones'),
        ('notificaciones.tasks.notificar_capacitacion_por_vencer_7_dias', 'Notificar capacitaciones por vencer (7 días)'),
        ('notificaciones.tasks.notificar_capacitacion_por_vencer_1_dia', 'Notificar capacitaciones por vencer (1 día)'),
        ('notificaciones.tasks.desactivar_capacitaciones', 'Desactivar capacitaciones'),
        ('notificaciones.tasks.notificar_jefes_por_colaboradores_sin_progreso', 'Notificar a jefes sobre sin progreso'),
    ]
    
    todas_tareas = tareas_notificaciones
    registradas = current_app.tasks
    
    print("\n📩 TAREAS DE NOTIFICACIONES:")
    for nombre_tarea, descripcion in tareas_notificaciones:
        if nombre_tarea in registradas:
            print(f"   ✅ {nombre_tarea}")
            print(f"      └─ {descripcion}")
        else:
            print(f"   ❌ {nombre_tarea}")
            print(f"      └─ FALTA REGISTRAR - {descripcion}")
    
    print()
    
    # 4. Verificar consistencia de tareas en beat_schedule vs funciones
    print("4️⃣ VERIFICANDO CONSISTENCIA DE CONFIGURACIÓN")
    print("-" * 80)
    
    beat_tasks = [config['task'] for config in beat_schedule.values()]
    missing_in_beat = []
    extra_in_beat = []
    
    # Verificar que todas las tareas de los que se esperan están en beat_schedule
    todas_tareas_esperadas = tareas_notificaciones
    for task_name, _ in todas_tareas_esperadas:
        if task_name not in beat_tasks:
            missing_in_beat.append(task_name)
    
    if missing_in_beat:
        print("\n❌ TAREAS FALTANTES EN BEAT SCHEDULE:")
        for task in missing_in_beat:
            print(f"   └─ {task}")
    else:
        print("\n✅ Todas las tareas están configuradas en beat_schedule")
    
    print()
    
    # 5. Resumen
    print("5️⃣ RESUMEN DE VERIFICACIÓN")
    print("-" * 80)
    
    total_tasks = len(todas_tareas)
    registered_tasks = sum(1 for t, _ in todas_tareas if t in registradas)
    configured_tasks = len([c for c in beat_schedule.values()])
    
    print(f"\n📊 Estadísticas:")
    print(f"   • Total de tareas esperadas: {total_tasks}")
    print(f"   • Tareas registradas en Celery: {registered_tasks}/{total_tasks}")
    print(f"   • Tareas configuradas en Beat: {configured_tasks}")
    
    if registered_tasks == total_tasks and not missing_in_beat:
        print(f"\n✅ ¡TODAS LAS TAREAS ESTÁN CORRECTAMENTE CONFIGURADAS!")
    else:
        print(f"\n⚠️ EXISTEN PROBLEMAS EN LA CONFIGURACIÓN - Revisa los errores arriba")
    
    print()
    print("=" * 80)
    print("INSTRUCCIONES PARA EJECUTAR CELERY:")
    print("-" * 80)
    print("""
1. Ejecutar Celery Worker:
   celery -A core worker -l info
   
   O en modo detached:
   celery -A core worker -l info --logfile=celery.log &

2. Ejecutar Celery Beat (Scheduler):
   celery -A core beat -l info
   
   O en modo detached:
   celery -A core beat -l info --logfile=celery-beat.log &

3. Monitorear tareas:
   celery -A core events
   
4. Ver logs de Docker:
   docker-compose logs -f backend
   docker-compose logs -f redis
   """)
    print("=" * 80)

if __name__ == '__main__':
    verificar_tareas()
