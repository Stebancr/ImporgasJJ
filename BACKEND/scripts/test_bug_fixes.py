#!/usr/bin/env python
"""
Script de prueba para validar que los fixes de los bugs #1 y #2 funcionan correctamente.

BUG #1: Módulos vacíos NO deben marcar capacitación como completada
BUG #2: Validación de coherencia - capacitación requiere ALL módulos completados

Uso: python manage.py shell < test_bug_fixes.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from capacitaciones.models import (
    Capacitaciones, Modulos, Lecciones,
    progresoCapacitaciones, progresoModulo, progresolecciones
)
from usuarios.models import Colaboradores
from capacitaciones.utils import (
    actualizar_progreso_leccion,
    actualizar_progreso_modulo,
    actualizar_progreso_capacitacion
)

print("\n" + "="*80)
print("🧪 TEST DE FIXES - BUG #1 Y BUG #2")
print("="*80 + "\n")

# ============================================================================
# TEST #1: BUG #1 - Módulos vacíos no deben marcar capacitación como completada
# ============================================================================
print("📋 TEST #1: BUG #1 - Módulos vacíos")
print("-" * 80)

try:
    # Obtener o crear datos de prueba
    cap = Capacitaciones.objects.filter(estado=1).first()
    colaborador = Colaboradores.objects.filter(estadocolaborador=1).first()
    
    if not cap or not colaborador:
        print("❌ No hay capacitaciones o colaboradores activos para probar")
    else:
        print(f"✓ Usando Capacitación: {cap.titulo} (ID:{cap.id})")
        print(f"✓ Usando Colaborador: {colaborador.nombrecolaborador} (ID:{colaborador.idcolaborador})")
        
        # Crear progreso de capacitación (inicial)
        prog_cap, _ = progresoCapacitaciones.objects.get_or_create(
            colaborador=colaborador,
            capacitacion=cap,
            defaults={'progreso': 0, 'completada': 0}
        )
        print(f"\n→ Progreso inicial: {prog_cap.progreso}%, completada={prog_cap.completada}")
        
        # Obtener módulos
        modulos = Modulos.objects.filter(idcapacitacion=cap)[:2]  # Primeros 2 módulos
        
        if not modulos.exists():
            print("⚠️  La capacitación no tiene módulos")
        else:
            print(f"\n📦 Probando con {modulos.count()} módulos:")
            
            for modulo in modulos:
                lecciones = Lecciones.objects.filter(idmodulo=modulo)
                print(f"\n   Módulo '{modulo.nombremodulo}' (ID:{modulo.id})")
                print(f"   └─ Lecciones: {lecciones.count()}")
                
                # Llamar a actualizar_progreso_modulo
                resultado = actualizar_progreso_modulo(colaborador.idcolaborador, modulo)
                
                # Verificar que se creó el registro
                prog_mod = progresoModulo.objects.filter(
                    colaborador=colaborador,
                    modulo=modulo
                ).first()
                
                if prog_mod:
                    print(f"   ✓ Progreso Módulo: {prog_mod.progreso}%, completada={prog_mod.completada}")
                    
                    # VALIDACIÓN FIX #1
                    if lecciones.count() == 0 and prog_mod.completada == 1:
                        print(f"   ❌ BUG #1 NO CORREGIDO: Módulo vacío pero completada=1")
                    elif lecciones.count() == 0 and prog_mod.completada == 0:
                        print(f"   ✅ BUG #1 CORREGIDO: Módulo vacío y completada=0")
            
            # Actualizar capacitación
            prog_cap.refresh_from_db()
            print(f"\n→ Progreso capacitación final: {prog_cap.progreso}%, completada={prog_cap.completada}")
            
            modulos_completados = progresoModulo.objects.filter(
                colaborador=colaborador,
                modulo__idcapacitacion=cap,
                completada=1
            ).count()
            total_modulos = modulos.count()
            
            print(f"\n📊 Resultado: {modulos_completados}/{total_modulos} módulos completados")
            if modulos_completados == total_modulos and modulos_completados > 0:
                if prog_cap.completada == 1:
                    print("   ✅ Capacitación marcada como completada (correcto si hay progreso real)")
                else:
                    print("   ❌ Capacitación NO completada pero módulos sí")
            else:
                if prog_cap.completada == 0:
                    print("   ✅ Capacitación NO completada (correcto - módulos no todos completos)")
                else:
                    print("   ❌ BUG #1: Capacitación completada pero módulos no todos listos")
        
except Exception as e:
    print(f"❌ Error en TEST #1: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST #2: BUG #2 - Validación de coherencia
# ============================================================================
print("\n\n📋 TEST #2: BUG #2 - Validación de coherencia")
print("-" * 80)

try:
    cap2 = Capacitaciones.objects.filter(estado=1).exclude(id=cap.id).first() if 'cap' in locals() else Capacitaciones.objects.filter(estado=1).first()
    colaborador2 = Colaboradores.objects.filter(estadocolaborador=1).first()
    
    if not cap2 or not colaborador2:
        print("❌ No hay datos para la prueba de coherencia")
    else:
        print(f"✓ Usando Capacitación: {cap2.titulo} (ID:{cap2.id})")
        print(f"✓ Usando Colaborador: {colaborador2.nombrecolaborador} (ID:{colaborador2.idcolaborador})")
        
        # Crear una inconsistencia manual: progresoModulo con completada=1 pero progreso<100
        modulos2 = Modulos.objects.filter(idcapacitacion=cap2)[:1]
        
        if modulos2.exists():
            modulo = modulos2.first()
            
            # Crear progreso de módulo inconsistente
            prog_mod_incon, _ = progresoModulo.objects.update_or_create(
                colaborador=colaborador2,
                modulo=modulo,
                defaults={
                    'progreso': 50,      # ⚠️ Progreso bajo
                    'completada': 1,     # ⚠️ Pero marcado como completado
                    'fecha_completado': timezone.now()
                }
            )
            
            print(f"\n→ Creado inconsistencia: progreso={prog_mod_incon.progreso}%, completada={prog_mod_incon.completada}")
            
            # Llamar a actualizar_progreso_capacitacion
            print("\n→ Llamando actualizar_progreso_capacitacion()...")
            actualizar_progreso_capacitacion(colaborador2.idcolaborador, cap2)
            
            # Verificar que se corrigió
            prog_mod_incon.refresh_from_db()
            print(f"\n✓ Después de actualizar: progreso={prog_mod_incon.progreso}%, completada={prog_mod_incon.completada}")
            
            # VALIDACIÓN FIX #2
            if prog_mod_incon.completada == 0:
                print("   ✅ BUG #2 CORREGIDO: Inconsistencia detectada y corregida")
            else:
                print("   ❌ BUG #2 NO CORREGIDO: Inconsistencia sigue presente")
        else:
            print("⚠️  Capacitación sin módulos para probar coherencia")

except Exception as e:
    print(f"❌ Error en TEST #2: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ TESTS COMPLETADOS")
print("="*80 + "\n")
