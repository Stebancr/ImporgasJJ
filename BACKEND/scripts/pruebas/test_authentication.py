#!/usr/bin/env python
"""
Test script to validate that all capacitaciones endpoints require authentication
"""
import os
import django
import requests
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from rest_framework.test import APIClient
from rest_framework import status

# Base URL for tests
BASE_URL = 'http://localhost:8000'

def test_authentication_required():
    """Test that all capacitaciones endpoints require authentication"""
    
    client = APIClient()
    
    endpoints = [
        # GET endpoints
        {'method': 'GET', 'url': '/capacitaciones/capacitaciones/', 'name': 'List Capacitaciones'},
        {'method': 'GET', 'url': '/capacitaciones/capacitacion/48/', 'name': 'Detail Capacitacion'},
        {'method': 'GET', 'url': '/capacitaciones/progreso/1/', 'name': 'Ver Progreso'},
        {'method': 'GET', 'url': '/capacitaciones/mis-capacitaciones/48/', 'name': 'Mis Capacitaciones (Detail)'},
        {'method': 'GET', 'url': '/capacitaciones/mis-capacitaciones/', 'name': 'Mis Capacitaciones (List)'},
        {'method': 'GET', 'url': '/capacitaciones/progreso/48/1/', 'name': 'Admin Progreso'},
        {'method': 'GET', 'url': '/capacitaciones/descargar-certificado/1/48/', 'name': 'Descargar Certificado'},
        
        # POST endpoints
        {'method': 'POST', 'url': '/capacitaciones/crear-capacitacion/', 'name': 'Crear Capacitacion', 'data': {'titulo': 'Test'}},
        {'method': 'POST', 'url': '/capacitaciones/progreso/registrar/', 'name': 'Registrar Progreso', 'data': {'leccion_id': 1}},
        {'method': 'POST', 'url': '/capacitaciones/leccion/1/completar/', 'name': 'Completar Leccion', 'data': {}},
        {'method': 'POST', 'url': '/capacitaciones/leccion/1/responder/', 'name': 'Responder Cuestionario', 'data': {}},
        {'method': 'POST', 'url': '/capacitaciones/previsualizar-colaboradores/', 'name': 'Previsualizar Colaboradores', 'data': {}},
        {'method': 'POST', 'url': '/capacitaciones/cargar-archivo/', 'name': 'Cargar Archivo', 'data': {}},
    ]
    
    print("\n=== Validación de Autenticación - Endpoints de Capacitaciones ===\n")
    
    failed_auth = []
    passed_auth = []
    
    for endpoint in endpoints:
        method = endpoint['method']
        url = endpoint['url']
        name = endpoint['name']
        data = endpoint.get('data', {})
        
        try:
            if method == 'GET':
                response = client.get(url)
            elif method == 'POST':
                response = client.post(url, data, format='json')
            
            # Unauthenticated requests should return 401 or 403
            if response.status_code in [401, 403]:
                passed_auth.append(f"✓ {name}: {response.status_code} (Autenticación requerida)")
            else:
                failed_auth.append(f"✗ {name}: {response.status_code} (Debería ser 401/403)")
        
        except Exception as e:
            # Connection errors are OK - means endpoint exists and rejects
            if '401' in str(e) or '403' in str(e):
                passed_auth.append(f"✓ {name}: 401/403 (Autenticación requerida)")
            else:
                failed_auth.append(f"? {name}: {str(e)[:50]}")
    
    # Print results
    print("AUTENTICACIÓN CORRECTA:")
    for result in passed_auth:
        print(result)
    
    if failed_auth:
        print("\n⚠️ PROBLEMAS DE AUTENTICACIÓN:")
        for result in failed_auth:
            print(result)
    else:
        print(f"\n✅ Todos los {len(passed_auth)} endpoints requieren autenticación correctamente")
    
    print("\n=== Validación Completada ===\n")

if __name__ == '__main__':
    test_authentication_required()
