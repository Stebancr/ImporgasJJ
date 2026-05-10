# -*- coding: utf-8 -*-
"""
Script para probar generacion de certificado
"""
import requests
import os

BASE_URL = "http://127.0.0.1:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzk5MTI2NDI1LCJpYXQiOjE3Njc1OTA0MjUsImp0aSI6ImUwOTg1NGNhZjdjNDQ0NGI4YWY4NTkxOGM2ZDAxNTE0IiwidXNlcl9pZCI6IjU1In0.d5_Dl5JQWjV4-zxm2k9X5vfqpesbjH2P--uSV_Dow1g"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

print("=" * 80)
print("PRUEBA: Generar certificado para capacitacion 46")
print("=" * 80)

id_capacitacion = 46
url = f"{BASE_URL}/capacitaciones/certificado/{id_capacitacion}/"

print(f"\nURL: {url}")
print(f"Token: {TOKEN[:50]}...")

try:
    print("\nEnviando peticion...")
    response = requests.get(url, headers=HEADERS, stream=True)
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    
    if response.status_code == 200:
        # Crear directorio media si no existe
        os.makedirs('media/test_certificados', exist_ok=True)
        
        # Guardar PDF
        filename = f'media/test_certificados/certificado_cap_{id_capacitacion}.pdf'
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(filename)
        print(f"\nCERTIFICADO GENERADO EXITOSAMENTE")
        print(f"Archivo: {filename}")
        print(f"Tamano: {file_size / 1024:.2f} KB")
        print(f"Cache-Control: {response.headers.get('Cache-Control')}")
        
        # Segunda peticion para probar cache
        print("\n\nPrueba de CACHE - Segunda descarga...")
        import time
        time.sleep(1)
        
        response2 = requests.get(url, headers=HEADERS, stream=True)
        if response2.status_code == 200:
            filename2 = f'media/test_certificados/certificado_cap_{id_capacitacion}_cache.pdf'
            with open(filename2, 'wb') as f:
                for chunk in response2.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Segunda descarga exitosa (desde cache)")
            print(f"Archivo: {filename2}")
        
    else:
        print(f"\nERROR:")
        try:
            error_data = response.json()
            print(f"Error: {error_data.get('error')}")
            if 'traceback' in error_data:
                print(f"\nTraceback:")
                print(error_data['traceback'])
        except:
            print(response.text)

except requests.exceptions.ConnectionError:
    print("\nERROR: No se puede conectar al servidor")
    print("Asegurate de que el servidor este corriendo:")
    print("  .\\venv\\Scripts\\python.exe manage.py runserver")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
