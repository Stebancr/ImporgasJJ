#!/usr/bin/env python
"""
Script para crear usuarios de prueba y sus tokens de autenticación
para usar en Postman con Bearer Token
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuarios
from rest_framework.authtoken.models import Token

def create_test_users():
    """Crea usuarios de prueba con sus tokens"""
    
    print("\n" + "="*70)
    print("GENERADOR DE TOKENS PARA POSTMAN - BEARER AUTHENTICATION")
    print("="*70 + "\n")
    
    users_to_create = [
        {
            'username': 'admin_test',
            'email': 'admin@test.com',
            'password': 'admin123',
            'tipousuario': 1,
            'description': 'Administrador'
        },
        {
            'username': 'superadmin_test',
            'email': 'superadmin@test.com',
            'password': 'super123',
            'tipousuario': 4,
            'description': 'SuperAdmin'
        },
        {
            'username': 'user_test',
            'email': 'user@test.com',
            'password': 'user123',
            'tipousuario': 0,
            'description': 'Usuario Normal'
        },
        {
            'username': 'lectura_admin_test',
            'email': 'lectura@test.com',
            'password': 'lectura123',
            'tipousuario': 2,
            'description': 'Admin de Lectura'
        },
    ]
    
    tokens = []
    
    for user_data in users_to_create:
        username = user_data['username']
        
        # Verificar si el usuario ya existe
        existing_user = Usuarios.objects.filter(usuario=username).first()
        
        if existing_user:
            print(f"⚠️  Usuario '{username}' ya existe. Obteniendo token...")
            user = existing_user
        else:
            # Crear el usuario
            user = Usuarios.objects.create_user(
                usuario=username,
                password=user_data['password'],
                tipousuario=user_data['tipousuario'],
                estadousuario=1
            )
            print(f"✅ Usuario '{username}' creado exitosamente")
        
        # Obtener o crear el token
        token, created = Token.objects.get_or_create(user=user)
        
        tokens.append({
            'username': user_data['username'],
            'email': user_data['email'],
            'password': user_data['password'],
            'tipousuario': user_data['tipousuario'],
            'description': user_data['description'],
            'token': token.key
        })
    
    # Mostrar los tokens
    print("\n" + "="*70)
    print("TOKENS GENERADOS - USA ESTOS EN POSTMAN")
    print("="*70 + "\n")
    
    for token_data in tokens:
        print(f"📝 {token_data['description']} ({token_data['username']})")
        print(f"   Email: {token_data['email']}")
        print(f"   Contraseña: {token_data['password']}")
        print(f"   tipousuario: {token_data['tipousuario']}")
        print(f"   Token: {token_data['token']}")
        print()
    
    # Crear archivo de configuración Postman
    print("="*70)
    print("INSTRUCCIONES PARA POSTMAN")
    print("="*70 + "\n")
    
    print("1️⃣  OBTENER TOKEN:")
    print("   POST http://localhost:8000/auth/get-token/")
    print("   Body (raw JSON):")
    print("   {")
    print("       \"username\": \"admin_test\",")
    print("       \"password\": \"admin123\"")
    print("   }\n")
    
    print("2️⃣  USAR TOKEN EN REQUESTS:")
    print("   Header: Authorization")
    print("   Valor: Bearer <token>\n")
    
    print("3️⃣  EJEMPLO CON CURL:")
    print("   curl -H 'Authorization: Bearer <token>' \\")
    print("        http://localhost:8000/capacitaciones/capacitaciones/\n")
    
    print("="*70)
    print("📋 RESUMEN DE USUARIOS (tipousuario)")
    print("="*70 + "\n")
    
    print(f"Total de usuarios creados/actualizados: {len(tokens)}\n")
    
    tipo_desc = {
        0: "👤 Usuario Normal",
        1: "⚙️  Administrador",
        2: "📖 Lectura Admin",
        3: "⭐ Usuario Especial",
        4: "👑 Super Admin"
    }
    
    for token_data in tokens:
        tipo_str = tipo_desc.get(token_data['tipousuario'], "❓ Desconocido")
        print(f"{tipo_str:25} | {token_data['username']:20} | tipousuario: {token_data['tipousuario']}")
    
    print("\n" + "="*70)
    print("✨ TODO LISTO PARA USAR EN POSTMAN")
    print("="*70 + "\n")

if __name__ == '__main__':
    create_test_users()
