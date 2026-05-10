#!/usr/bin/env python
"""
Script de diagnóstico para verificar tokens y permisos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.authtoken.models import Token
from usuarios.models import Usuarios

def diagnosticar_tokens():
    print("\n" + "="*70)
    print("DIAGNÓSTICO DE TOKENS Y USUARIOS")
    print("="*70 + "\n")
    
    # Listar todos los tokens
    tokens = Token.objects.select_related('user').all()
    
    if not tokens:
        print("⚠️  NO HAY TOKENS EN LA BASE DE DATOS\n")
        print("Necesitas crear tokens primero. Ejecuta:")
        print("   python create_test_tokens.py\n")
        return
    
    print(f"📊 Total de tokens encontrados: {tokens.count()}\n")
    
    tipo_desc = {
        0: "👤 Usuario Normal",
        1: "⚙️  Administrador",
        2: "📖 Lectura Admin",
        3: "⭐ Usuario Especial",
        4: "👑 Super Admin"
    }
    
    print("TOKENS DISPONIBLES:")
    print("-" * 70)
    
    for token in tokens:
        user = token.user
        tipo_usuario = getattr(user, 'tipousuario', 'N/A')
        tipo_str = tipo_desc.get(tipo_usuario, f"❓ Tipo {tipo_usuario}")
        
        # Verificar si puede acceder a capacitaciones
        puede_ver_capacitaciones = tipo_usuario in [1, 4]
        acceso = "✅ SÍ" if puede_ver_capacitaciones else "❌ NO"
        
        print(f"\n👤 Usuario: {user.usuario}")
        print(f"   Token: {token.key}")
        print(f"   Tipo: {tipo_str} (tipousuario={tipo_usuario})")
        print(f"   Acceso a /capacitaciones/capacitaciones/: {acceso}")
    
    print("\n" + "="*70)
    print("INSTRUCCIONES PARA POSTMAN")
    print("="*70 + "\n")
    
    # Encontrar un admin
    admin_token = None
    for token in tokens:
        if getattr(token.user, 'tipousuario', None) in [1, 4]:
            admin_token = token
            break
    
    if admin_token:
        print("✅ Token de Administrador encontrado:\n")
        print(f"   Usuario: {admin_token.user.usuario}")
        print(f"   Token: {admin_token.key}\n")
        print("📋 Copia este token y úsalo en Postman:\n")
        print("   1. Abre Postman")
        print("   2. Ve a Authorization → Type: Bearer Token")
        print("   3. Pega este token:")
        print(f"   {admin_token.key}\n")
        print("   4. Haz GET a: http://localhost:8000/capacitaciones/capacitaciones/")
    else:
        print("⚠️  NO HAY TOKENS DE ADMINISTRADOR\n")
        print("Necesitas crear un usuario admin. En Django shell ejecuta:\n")
        print("   from usuarios.models import Usuarios")
        print("   from rest_framework.authtoken.models import Token")
        print("   user = Usuarios.objects.get(usuario='tu_usuario')")
        print("   user.tipousuario = 1")
        print("   user.save()")
        print("   token, _ = Token.objects.get_or_create(user=user)")
        print(f"   print(token.key)")
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    diagnosticar_tokens()
