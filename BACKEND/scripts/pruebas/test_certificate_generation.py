#!/usr/bin/env python
"""
Script para probar la generación de certificados PDF completa
"""
import os
import sys
import django
import requests
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework_simplejwt.tokens import AccessToken
from usuarios.models import Usuarios
from capacitaciones.models import Capacitaciones, progresoCapacitaciones, Colaboradores

# Configuración
BASE_URL = 'http://127.0.0.1:8000'
USER_ID = 55
CAPACITACION_ID = 46

print("=" * 70)
print("PRUEBA DE GENERACIÓN DE CERTIFICADOS PDF")
print("=" * 70)

# 1. Verificar usuario
print("\n1️⃣  Verificando usuario...")
try:
    user = Usuarios.objects.get(pk=USER_ID)
    print(f"   ✓ Usuario ID: {user.id}")
    print(f"   ✓ Username: {user.username}")
    
    if hasattr(user, 'id_colaboradoru'):
        if user.id_colaboradoru:
            print(f"   ✓ Colaborador ID: {user.id_colaboradoru.idcolaborador}")
            print(f"   ✓ Nombre: {user.id_colaboradoru.nombrecolaborador}")
            print(f"   ✓ Cédula: {user.id_colaboradoru.cccolaborador}")
        else:
            print("   ⚠ Usuario no tiene colaborador asociado")
    else:
        print("   ⚠ Usuario no tiene atributo id_colaboradoru")
except Usuarios.DoesNotExist:
    print(f"   ✗ Usuario {USER_ID} no encontrado")
    sys.exit(1)

# 2. Verificar capacitación
print("\n2️⃣  Verificando capacitación...")
try:
    capacitacion = Capacitaciones.objects.get(id=CAPACITACION_ID)
    print(f"   ✓ Capacitación ID: {capacitacion.id}")
    print(f"   ✓ Título: {capacitacion.titulo}")
except Capacitaciones.DoesNotExist:
    print(f"   ✗ Capacitación {CAPACITACION_ID} no encontrada")
    sys.exit(1)

# 3. Verificar progreso
print("\n3️⃣  Verificando progreso...")
try:
    colaborador = user.id_colaboradoru
    progreso = progresoCapacitaciones.objects.filter(
        colaborador=colaborador,
        capacitacion=capacitacion,
        completada=1
    ).first()
    
    if progreso:
        print(f"   ✓ Progreso encontrado")
        print(f"   ✓ Completada: {progreso.completada}")
        print(f"   ✓ Fecha completada: {progreso.fecha_completada}")
    else:
        print(f"   ⚠ El colaborador NO ha completado esta capacitación")
        print("   ℹ  Creando progreso de prueba...")
        progresoCapacitaciones.objects.create(
            colaborador=colaborador,
            capacitacion=capacitacion,
            completada=1
        )
        print("   ✓ Progreso creado")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")
    sys.exit(1)

# 4. Generar token JWT
print("\n4️⃣  Generando token JWT...")
try:
    token = AccessToken.for_user(user)
    token_str = str(token)
    print(f"   ✓ Token generado")
    print(f"   ✓ Token (primeros 50 chars): {token_str[:50]}...")
except Exception as e:
    print(f"   ✗ Error al generar token: {str(e)}")
    sys.exit(1)

# 5. Hacer petición al endpoint
print("\n5️⃣  Haciendo petición al servidor...")
headers = {
    'Authorization': f'Bearer {token_str}',
    'Content-Type': 'application/json'
}

url = f'{BASE_URL}/capacitaciones/certificado/{CAPACITACION_ID}/'
print(f"   📤 URL: {url}")
print(f"   📋 Esperando respuesta...")

try:
    # Timeout mayor para dar tiempo a la conversión
    response = requests.get(url, headers=headers, timeout=120)
    print(f"\n6️⃣  Respuesta recibida")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✓ ¡ÉXITO! Certificado PDF generado")
        print(f"   ✓ Tamaño: {len(response.content):,} bytes")
        
        # Guardar PDF
        pdf_path = 'certificado_test_' + time.strftime('%Y%m%d_%H%M%S') + '.pdf'
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        print(f"   ✓ PDF guardado en: {os.path.abspath(pdf_path)}")
        
        # Validar que es un PDF válido
        if response.content.startswith(b'%PDF'):
            print(f"   ✓ PDF válido (comienza con %PDF)")
        else:
            print(f"   ⚠ Advertencia: El archivo no comienza con %PDF")
        
        print("\n" + "=" * 70)
        print("✅ PRUEBA EXITOSA")
        print("=" * 70)
        
    elif response.status_code == 400:
        print(f"   ✗ Error 400 (Bad Request)")
        try:
            error_data = response.json()
            print(f"   Detalles: {error_data}")
        except:
            print(f"   Respuesta: {response.text[:500]}")
            
    elif response.status_code == 403:
        print(f"   ✗ Error 403 (Forbidden - Permisos insuficientes)")
        try:
            error_data = response.json()
            print(f"   Detalles: {error_data}")
        except:
            print(f"   Respuesta: {response.text[:500]}")
            
    elif response.status_code == 500:
        print(f"   ✗ Error 500 (Server Error)")
        try:
            error_data = response.json()
            print(f"   Error: {error_data.get('error', 'Unknown')}")
            if 'traceback' in error_data:
                print(f"   Traceback:\n{error_data['traceback'][:1000]}")
        except:
            print(f"   Respuesta: {response.text[:1000]}")
    else:
        print(f"   ✗ Error {response.status_code}")
        print(f"   Respuesta: {response.text[:500]}")
        
except requests.exceptions.ConnectionError:
    print("   ✗ No se puede conectar al servidor")
    print("   ℹ  ¿Está el servidor ejecutándose en http://127.0.0.1:8000?")
    print("   ℹ  Ejecuta: python manage.py runserver")
except requests.exceptions.Timeout:
    print("   ✗ Timeout - La conversión tardó demasiado")
    print("   ℹ  Puede estar procesando un archivo grande")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()
