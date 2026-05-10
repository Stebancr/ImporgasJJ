#!/usr/bin/env python
"""
Script para ejecutar el servidor y probar certificados
"""
import subprocess
import time
import sys
import os

print("🚀 Iniciando servidor Django...")
print("=" * 70)

# Cambiar a directorio del proyecto
os.chdir('C:\\Users\\PC\\Documents\\trabajo\\LMS-backend')

# Iniciar servidor en background
server_process = subprocess.Popen(
    ['python', 'manage.py', 'runserver', '0.0.0.0:8000'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print("⏳ Esperando que el servidor inicie (10 segundos)...")
time.sleep(10)

try:
    # Ejecutar prueba
    print("\n🧪 Ejecutando prueba de certificados...\n")
    result = subprocess.run(
        ['python', 'test_certificate_generation.py'],
        timeout=180
    )
    sys.exit(result.returncode)
    
finally:
    # Detener servidor
    print("\n🛑 Deteniendo servidor...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    print("✓ Servidor detenido")
