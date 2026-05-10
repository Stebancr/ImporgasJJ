"""
Script para validar el endpoint de previsualizar colaboradores desde CSV
POST /capacitaciones/cargar/
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Token JWT del usuario autenticado
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MDM5NTIzLCJpYXQiOjE3MzYwMzU5MjMsImp0aSI6ImE0NDQwZjY3OGY2MTQ0YWRhNTcyZGViMTZjMzhlMWM4IiwidXNlcl9pZCI6NTV9.E-9JFXx8F_PW6s6VUpNoxJR_AYH5J2lp50vwIEcKD2M"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def test_cargar_csv_colaboradores():
    """
    Test: Cargar archivo CSV con cédulas y previsualizar colaboradores
    """
    print("\n" + "="*80)
    print("TEST: Previsualizar Colaboradores desde CSV")
    print("="*80)
    
    url = f"{BASE_URL}/capacitaciones/cargar/"
    
    # Leer el archivo CSV de ejemplo
    try:
        with open('ejemplo_colaboradores.csv', 'rb') as archivo:
            files = {'archivo': ('colaboradores.csv', archivo, 'text/csv')}
            
            response = requests.post(url, headers=HEADERS, files=files)
            
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ Archivo procesado exitosamente")
                print(f"Total procesados: {result.get('total_procesados')}")
                print(f"Encontrados: {result.get('encontrados')}")
                print(f"No encontrados: {result.get('no_encontrados')}")
                
                if result.get('colaboradores'):
                    print("\n--- Colaboradores Encontrados ---")
                    for colab in result['colaboradores']:
                        print(f"\nCédula: {colab.get('cedula')}")
                        print(f"Nombre: {colab.get('nombre')} {colab.get('apellido')}")
                        print(f"Correo: {colab.get('correo')}")
                        print(f"Cargo: {colab.get('cargo')}")
                        print(f"Estado: {colab.get('estado')}")
                
                if result.get('no_encontrados_detalle'):
                    print("\n--- No Encontrados ---")
                    for no_encontrado in result['no_encontrados_detalle']:
                        print(f"Cédula: {no_encontrado.get('cedula')} - {no_encontrado.get('motivo')}")
            else:
                print(f"\n❌ Error: {response.json()}")
                
    except FileNotFoundError:
        print("\n❌ Error: No se encontró el archivo 'ejemplo_colaboradores.csv'")
        print("Crea el archivo con el siguiente formato:")
        print("cedula")
        print("1234567890")
        print("0987654321")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error de conexión: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_sin_archivo():
    """
    Test: Intentar enviar sin archivo
    """
    print("\n" + "="*80)
    print("TEST: Validación - Sin archivo")
    print("="*80)
    
    url = f"{BASE_URL}/capacitaciones/cargar/"
    
    try:
        response = requests.post(url, headers=HEADERS)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 400:
            print("\n✅ Validación correcta: Se requiere un archivo")
        else:
            print("\n❌ Error: Debería retornar 400 Bad Request")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_archivo_no_csv():
    """
    Test: Intentar enviar un archivo que no es CSV
    """
    print("\n" + "="*80)
    print("TEST: Validación - Archivo no CSV")
    print("="*80)
    
    url = f"{BASE_URL}/capacitaciones/cargar/"
    
    try:
        # Crear un archivo de texto temporal
        with open('temp_test.txt', 'w') as f:
            f.write("Este es un archivo de texto")
        
        with open('temp_test.txt', 'rb') as archivo:
            files = {'archivo': ('test.txt', archivo, 'text/plain')}
            
            response = requests.post(url, headers=HEADERS, files=files)
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            
            if response.status_code == 400:
                print("\n✅ Validación correcta: Solo se aceptan archivos CSV")
            else:
                print("\n❌ Error: Debería retornar 400 Bad Request")
        
        # Limpiar archivo temporal
        import os
        os.remove('temp_test.txt')
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_csv_sin_columna_cedula():
    """
    Test: CSV sin la columna 'cedula'
    """
    print("\n" + "="*80)
    print("TEST: Validación - CSV sin columna 'cedula'")
    print("="*80)
    
    url = f"{BASE_URL}/capacitaciones/cargar/"
    
    try:
        # Crear CSV temporal sin columna cedula
        with open('temp_invalid.csv', 'w') as f:
            f.write("nombre,apellido\n")
            f.write("Juan,Pérez\n")
        
        with open('temp_invalid.csv', 'rb') as archivo:
            files = {'archivo': ('invalid.csv', archivo, 'text/csv')}
            
            response = requests.post(url, headers=HEADERS, files=files)
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
            
            if response.status_code == 400:
                print("\n✅ Validación correcta: Se requiere columna 'cedula'")
            else:
                print("\n❌ Error: Debería retornar 400 Bad Request")
        
        # Limpiar archivo temporal
        import os
        os.remove('temp_invalid.csv')
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def crear_csv_ejemplo():
    """
    Crear archivo CSV de ejemplo con cédulas
    """
    print("\n" + "="*80)
    print("CREANDO ARCHIVO CSV DE EJEMPLO")
    print("="*80)
    
    # Consultar base de datos para obtener cédulas reales
    print("\nPara crear un CSV de prueba válido, necesitas cédulas reales de tu base de datos.")
    print("Ejecuta esta consulta SQL:")
    print("\n  SELECT cccolaborador FROM colaboradores WHERE estadocolaborador = 1 LIMIT 5;")
    print("\nLuego crea un archivo 'ejemplo_colaboradores.csv' con este formato:")
    print("\ncedula")
    print("1234567890")
    print("0987654321")
    print("...\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("VALIDACIÓN DEL ENDPOINT: PREVISUALIZAR COLABORADORES CSV")
    print("="*80)
    
    # Primero verificar si existe el archivo de ejemplo
    import os
    if not os.path.exists('ejemplo_colaboradores.csv'):
        crear_csv_ejemplo()
        input("\nPresiona ENTER después de crear el archivo CSV...")
    
    test_cargar_csv_colaboradores()
    test_sin_archivo()
    test_archivo_no_csv()
    test_csv_sin_columna_cedula()
    
    print("\n" + "="*80)
    print("TESTS COMPLETADOS")
    print("="*80)
