#!/usr/bin/env python
"""
Script para probar el endpoint de completar lección
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from usuarios.models import Usuarios, Colaboradores
from capacitaciones.models import Capacitaciones, Modulos, Lecciones

def test_completar_leccion():
    """Prueba el endpoint de completar lección"""
    
    print("\n" + "="*70)
    print("TEST: Completar Lección - POST /capacitaciones/leccion/{id}/completar/")
    print("="*70 + "\n")
    
    # Buscar datos existentes
    leccion = Lecciones.objects.first()
    if not leccion:
        print("❌ No hay lecciones en la base de datos")
        return
    
    colaborador = Colaboradores.objects.first()
    if not colaborador:
        print("❌ No hay colaboradores en la base de datos")
        return
    
    # Buscar un usuario con token
    usuario = Usuarios.objects.filter(tipousuario__in=[0, 1, 4]).first()
    if not usuario:
        print("❌ No hay usuarios disponibles")
        return
    
    # Obtener o crear token
    token, created = Token.objects.get_or_create(user=usuario)
    
    print(f"📋 Datos de prueba:")
    print(f"   Lección ID: {leccion.id}")
    print(f"   Título: {leccion.tituloleccion}")
    print(f"   Módulo: {leccion.idmodulo.nombremodulo if leccion.idmodulo else 'N/A'}")
    print(f"   Capacitación: {leccion.idmodulo.idcapacitacion.titulo if leccion.idmodulo and leccion.idmodulo.idcapacitacion else 'N/A'}")
    print(f"   Colaborador ID: {colaborador.idcolaborador}")
    print(f"   Colaborador: {colaborador.nombrecolaborador} {colaborador.apellidocolaborador}")
    print(f"   Usuario: {usuario.usuario} (tipousuario={usuario.tipousuario})")
    print(f"   Token: {token.key[:20]}...\n")
    
    # Crear cliente API
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.key}')
    
    # Endpoint
    url = f'/capacitaciones/leccion/{leccion.id}/completar/'
    
    # Datos
    data = {
        'colaborador_id': colaborador.idcolaborador
    }
    
    print(f"🚀 Enviando request POST a: {url}")
    print(f"📦 Body: {data}\n")
    
    # Hacer request
    response = client.post(url, data, format='json')
    
    print(f"📥 RESPUESTA:")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ ÉXITO - Lección completada\n")
        print(f"📊 Datos de respuesta:")
        try:
            response_data = response.json()
            for key, value in response_data.items():
                print(f"   {key}: {value}")
        except:
            print(f"   {response.content}")
    elif response.status_code == 401:
        print(f"   ❌ ERROR - No autenticado")
        print(f"   Mensaje: {response.json() if response.content else 'Sin mensaje'}")
    elif response.status_code == 403:
        print(f"   ❌ ERROR - Sin permisos")
        print(f"   Mensaje: {response.json() if response.content else 'Sin mensaje'}")
    elif response.status_code == 404:
        print(f"   ❌ ERROR - No encontrado")
        print(f"   Mensaje: {response.json() if response.content else 'Sin mensaje'}")
    elif response.status_code == 400:
        print(f"   ❌ ERROR - Bad Request")
        print(f"   Mensaje: {response.json() if response.content else 'Sin mensaje'}")
    else:
        print(f"   ❌ ERROR")
        print(f"   Mensaje: {response.json() if response.content else 'Sin mensaje'}")
    
    print("\n" + "="*70)
    print("INFORMACIÓN PARA POSTMAN")
    print("="*70 + "\n")
    
    print(f"URL: http://localhost:8000{url}")
    print(f"Método: POST")
    print(f"Headers:")
    print(f"  Authorization: Bearer {token.key}")
    print(f"  Content-Type: application/json")
    print(f"Body (raw JSON):")
    print(f'  {{')
    print(f'    "colaborador_id": {colaborador.idcolaborador}')
    print(f'  }}')
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    test_completar_leccion()
