#!/usr/bin/env python
"""
Test script to validate that only admins and superusers can access 
GET /capacitaciones/capacitaciones/
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User

def test_capacitaciones_list_permissions():
    """Test that only admin and superuser can access capacitaciones list"""
    
    client = Client()
    endpoint = '/capacitaciones/capacitaciones/'
    
    print("\n=== Test: Validación de Permisos - GET /capacitaciones/capacitaciones/ ===\n")
    
    # Test 1: No autenticado
    print("1️⃣  TEST SIN AUTENTICACIÓN")
    response = client.get(endpoint)
    print(f"   Status: {response.status_code}")
    print(f"   Esperado: 403 (Forbidden)")
    if response.status_code == 403:
        print("   ✅ CORRECTO - No autenticado rechazado\n")
    else:
        print("   ❌ ERROR - Debería ser 403\n")
    
    # Test 2: Usuario normal (is_staff = False)
    print("2️⃣  TEST CON USUARIO NORMAL (is_staff=False)")
    try:
        # Clean up first
        User.objects.filter(username='test_user_normal').delete()
        
        # Create test user with is_staff = False
        user_normal = User.objects.create_user(
            username='test_user_normal',
            email='normal@test.com',
            password='testpass123',
            is_staff=False
        )
        
        client.login(username='test_user_normal', password='testpass123')
        response = client.get(endpoint)
        print(f"   Usuario: {user_normal.username} (is_staff={user_normal.is_staff})")
        print(f"   Status: {response.status_code}")
        print(f"   Esperado: 403 (Forbidden)")
        if response.status_code == 403:
            print("   ✅ CORRECTO - Usuario normal rechazado\n")
        else:
            print("   ❌ ERROR - Debería ser 403\n")
            if response.status_code == 200:
                print("   ⚠️  PROBLEMA: Usuario normal tiene acceso!\n")
        client.logout()
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}\n")
    
    # Test 3: Admin (is_staff = True)
    print("3️⃣  TEST CON ADMINISTRADOR (is_staff=True)")
    try:
        # Clean up first
        User.objects.filter(username='test_user_admin').delete()
        
        user_admin = User.objects.create_user(
            username='test_user_admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        
        client.login(username='test_user_admin', password='testpass123')
        response = client.get(endpoint)
        print(f"   Usuario: {user_admin.username} (is_staff={user_admin.is_staff})")
        print(f"   Status: {response.status_code}")
        print(f"   Esperado: 200 (OK)")
        if response.status_code == 200:
            print("   ✅ CORRECTO - Admin tiene acceso\n")
        else:
            print(f"   ❌ ERROR - Debería ser 200, recibió {response.status_code}\n")
        client.logout()
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}\n")
    
    print("=== Validación Completada ===\n")

if __name__ == '__main__':
    test_capacitaciones_list_permissions()
