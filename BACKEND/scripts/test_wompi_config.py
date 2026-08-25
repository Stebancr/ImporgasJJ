#!/usr/bin/env python
"""
Verificar configuración de Wompi en settings.py
"""
import os
import sys

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.conf import settings

print("=" * 70)
print("CONFIGURACIÓN DE WOMPI")
print("=" * 70)

print(f"\nWOMPI_PUBLIC_KEY: {settings.WOMPI_PUBLIC_KEY or '❌ NO CONFIGURADO'}")
print(f"WOMPI_PRIVATE_KEY: {'✅ Configurado' if settings.WOMPI_PRIVATE_KEY else '❌ NO CONFIGURADO'}")
print(f"WOMPI_EVENTS_SECRET: {'✅ Configurado' if settings.WOMPI_EVENTS_SECRET else '❌ NO CONFIGURADO'}")
print(f"WOMPI_INTEGRITY_SECRET: {settings.WOMPI_INTEGRITY_SECRET or '❌ NO CONFIGURADO'}")

if settings.WOMPI_INTEGRITY_SECRET:
    print(f"\n✅ WOMPI_INTEGRITY_SECRET está configurado ({len(settings.WOMPI_INTEGRITY_SECRET)} caracteres)")
    
    # Probar generación de signature
    import hashlib
    reference = "TEST-123"
    amount_in_cents = 180000000
    currency = "COP"
    
    signature_string = f"{reference}{amount_in_cents}{currency}{settings.WOMPI_INTEGRITY_SECRET}"
    signature = hashlib.sha256(signature_string.encode()).hexdigest()
    
    print(f"\n🔐 Prueba de generación de signature:")
    print(f"   Input: {signature_string}")
    print(f"   SHA-256: {signature}")
    print(f"   Longitud: {len(signature)} caracteres")
else:
    print(f"\n❌ WOMPI_INTEGRITY_SECRET no está configurado")
    print(f"   Verifica que esté en el archivo .env")

print("\n" + "=" * 70)
