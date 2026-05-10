"""
Script para validar el endpoint de descarga de certificados
GET /capacitaciones/certificado/<id_capacitacion>/
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Token JWT del usuario autenticado
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY3NTkwMzcwLCJpYXQiOjE3Njc1OTAwNzAsImp0aSI6IjU0YWE4NWZlNWNkZjRjYzE4NzFkODg1NjM5MWYxNmJlIiwidXNlcl9pZCI6IjU1In0.4vU_VazaksBgK8yYbqclAgHL_1Ac_uH-dlfPDpWcA84"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def test_descargar_certificado():
    """
    Test: Descargar certificado de una capacitación completada
    """
    print("\n" + "="*80)
    print("TEST: Descargar Certificado")
    print("="*80)
    
    # ID de capacitación 46
    id_capacitacion = 46
    
    url = f"{BASE_URL}/capacitaciones/certificado/{id_capacitacion}/"
    
    try:
        response = requests.get(url, headers=HEADERS, stream=True)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # Guardar PDF
            filename = f"certificado_capacitacion_{id_capacitacion}.pdf"
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"\n✅ Certificado descargado exitosamente: {filename}")
            print(f"Cache-Control: {response.headers.get('Cache-Control')}")
            
        elif response.status_code == 400:
            print(f"\n❌ Error: {response.json()}")
            print("Posible causa: Capacitación no completada o usuario sin colaborador")
            
        elif response.status_code == 403:
            print(f"\n❌ Error: No tienes permiso para descargar este certificado")
            
        elif response.status_code == 404:
            print(f"\n❌ Error: Capacitación no encontrada o plantilla no disponible")
            
        else:
            try:
                print(f"\nResponse: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            except:
                print(f"\nResponse: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error de conexión: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_certificado_no_completado():
    """
    Test: Intentar descargar certificado de capacitación no completada
    """
    print("\n" + "="*80)
    print("TEST: Certificado de capacitación no completada")
    print("="*80)
    
    # Usar ID de capacitación que no está completada
    id_capacitacion = 999
    
    url = f"{BASE_URL}/capacitaciones/certificado/{id_capacitacion}/"
    
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            print(f"Error (esperado): {result.get('error')}")
            print("\n✅ Validación correcta: No se puede descargar certificado sin completar capacitación")
        else:
            print(f"\nResponse: {response.json()}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_cache_certificado():
    """
    Test: Verificar que el certificado se cachea correctamente
    """
    print("\n" + "="*80)
    print("TEST: Caché de certificados (30 días)")
    print("="*80)
    
    id_capacitacion = 46
    url = f"{BASE_URL}/capacitaciones/certificado/{id_capacitacion}/"
    
    try:
        # Primera descarga
        print("\nPrimera descarga (generación)...")
        import time
        start = time.time()
        response1 = requests.get(url, headers=HEADERS)
        tiempo1 = time.time() - start
        
        if response1.status_code == 200:
            print(f"Tiempo: {tiempo1:.2f}s")
            print(f"Cache-Control: {response1.headers.get('Cache-Control')}")
            
            # Segunda descarga (desde caché)
            print("\nSegunda descarga (desde caché)...")
            start = time.time()
            response2 = requests.get(url, headers=HEADERS)
            tiempo2 = time.time() - start
            
            if response2.status_code == 200:
                print(f"Tiempo: {tiempo2:.2f}s")
                
                if tiempo2 < tiempo1:
                    print(f"\n✅ Caché funcionando: Segunda descarga {tiempo1/tiempo2:.1f}x más rápida")
                else:
                    print(f"\n⚠️  Segunda descarga no fue significativamente más rápida")
        else:
            print(f"\n❌ Error en primera descarga: {response1.json()}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def verificar_plantillas():
    """
    Verificar que existen las plantillas de certificados
    """
    print("\n" + "="*80)
    print("VERIFICACIÓN DE PLANTILLAS")
    print("="*80)
    
    import os
    
    plantillas = [
        'REGENCY.docx',
        'PROTINCO.docx',
        'CONSORCIO.docx',
        'REGENCY_HEALTH.docx',
        'REGENC_TECH.docx'
    ]
    
    plantillas_dir = 'plantillas'
    
    print(f"\nBuscando plantillas en: {os.path.abspath(plantillas_dir)}\n")
    
    for plantilla in plantillas:
        path = os.path.join(plantillas_dir, plantilla)
        if os.path.exists(path):
            print(f"✅ {plantilla}")
        else:
            print(f"❌ {plantilla} - NO ENCONTRADA")
    
    print("\nLas plantillas deben contener variables entre llaves {{}} como:")
    print("  - {{nombre_completo}}")
    print("  - {{nombre}}")
    print("  - {{apellido}}")
    print("  - {{cedula}}")
    print("  - {{capacitacion}}")
    print("  - {{fecha}}")
    print("  - {{fecha_corta}}")
    print("  - {{empresa}}")
    print("  - {{cargo}}")
    print("  - {{centro}}")


def info_uso():
    """
    Información sobre cómo usar el endpoint
    """
    print("\n" + "="*80)
    print("INFORMACIÓN DE USO")
    print("="*80)
    
    print("\n1. ENDPOINT SIMPLIFICADO (Recomendado):")
    print("   GET /capacitaciones/certificado/<id_capacitacion>/")
    print("   - Obtiene colaborador_id automáticamente del token JWT")
    print("   - Solo requiere el ID de la capacitación")
    
    print("\n2. ENDPOINT COMPLETO (Legacy):")
    print("   GET /capacitaciones/descargar-certificado/<id_colaborador>/<id_capacitacion>/")
    print("   - Requiere especificar colaborador_id y capacitacion_id")
    print("   - Valida que el token corresponda al colaborador solicitado")
    
    print("\n3. REQUISITOS:")
    print("   - Usuario autenticado con token JWT válido")
    print("   - Usuario debe tener un colaborador asociado")
    print("   - Capacitación debe estar completada al 100% (completada=1)")
    print("   - Colaborador debe tener empresa asociada")
    print("   - Debe existir plantilla para la empresa del colaborador")
    
    print("\n4. CACHÉ:")
    print("   - Certificados se cachean por 30 días")
    print("   - No se regeneran si ya existen (a menos que pasen 30 días)")
    print("   - Header: Cache-Control: max-age=2592000 (30 días)")
    
    print("\n5. VARIABLES EN PLANTILLAS:")
    print("   Las plantillas Word deben usar estas variables:")
    print("   {{nombre_completo}} - Nombre y apellido completo")
    print("   {{nombre}} - Solo nombre")
    print("   {{apellido}} - Solo apellido")
    print("   {{cedula}} - Cédula del colaborador")
    print("   {{capacitacion}} - Título de la capacitación")
    print("   {{fecha}} - Fecha larga (ej: 5 de enero de 2026)")
    print("   {{fecha_corta}} - Fecha corta (ej: 05/01/2026)")
    print("   {{empresa}} - Nombre de la empresa")
    print("   {{cargo}} - Cargo del colaborador")
    print("   {{centro}} - Centro operativo")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("VALIDACIÓN DEL ENDPOINT: DESCARGAR CERTIFICADO")
    print("="*80)
    
    info_uso()
    verificar_plantillas()
    
    input("\n\nPresiona ENTER para ejecutar los tests...")
    
    test_descargar_certificado()
    test_certificado_no_completado()
    test_cache_certificado()
    
    print("\n" + "="*80)
    print("TESTS COMPLETADOS")
    print("="*80)
