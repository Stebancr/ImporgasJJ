#!/usr/bin/env python
"""
Script para probar que el backend genere correctamente la signature de Wompi
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_crear_orden_wompi():
    """Crear una orden con Wompi y verificar que incluya signature"""
    
    print("=" * 70)
    print("PRUEBA: Creación de Orden Wompi con Signature")
    print("=" * 70)
    
    # Datos de la orden
    order_data = {
        "customer_name": "Usuario de Prueba Signature",
        "customer_email": "test_signature@example.com",
        "customer_phone": "+57 300 9999999",
        "shipping_address": "Calle Test #123-45",
        "city": "Bogotá",
        "department": "Cundinamarca",
        "postal_code": "110111",
        "payment_method": "wompi",
        "wompi_reference": f"TEST-SIGNATURE-{int(__import__('time').time())}",
        "notes": "Prueba de signature",
        "items": [
            {
                "product_id": 5,  # calentador prueba
                "quantity": 1
            }
        ]
    }
    
    print(f"\n📝 Creando orden con referencia: {order_data['wompi_reference']}")
    
    try:
        response = requests.post(
            f"{API_BASE}/orders",
            json=order_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            order = data.get('data', {})
            
            print(f"\n✅ Orden creada exitosamente!")
            print(f"   - Tracking Code: {order.get('tracking_code')}")
            print(f"   - Wompi Reference: {order.get('wompi_reference')}")
            print(f"   - Total: ${float(order.get('total', 0)):,.0f}")
            print(f"   - Payment Method: {order.get('payment_method')}")
            
            # Verificar signature
            signature = order.get('wompi_signature')
            if signature:
                print(f"\n🔐 Signature generada: {signature[:32]}...{signature[-8:]}")
                print(f"   Longitud: {len(signature)} caracteres (esperado: 64 para SHA-256)")
                
                if len(signature) == 64:
                    print("\n✅ PRUEBA EXITOSA: La signature se generó correctamente!")
                    
                    # Construir URL de Wompi
                    from urllib.parse import urlencode
                    params = {
                        'public-key': 'pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6',
                        'currency': 'COP',
                        'amount-in-cents': str(int(order['total'] * 100)),
                        'reference': order['wompi_reference'],
                        'customer-email': order_data['customer_email'],
                        'signature:integrity': signature
                    }
                    
                    wompi_url = f"https://checkout.wompi.co/p/?{urlencode(params)}"
                    print(f"\n🌐 URL de Wompi (primeros 150 caracteres):")
                    print(f"   {wompi_url[:150]}...")
                    
                    # Verificar que la URL contenga la signature
                    if 'signature%3Aintegrity=' in wompi_url or 'signature:integrity=' in wompi_url:
                        print("\n✅ La URL contiene el parámetro signature:integrity")
                    else:
                        print("\n❌ ERROR: La URL NO contiene el parámetro signature")
                        
                else:
                    print(f"\n❌ ERROR: Longitud de signature incorrecta ({len(signature)} != 64)")
            else:
                print("\n❌ ERROR: No se generó wompi_signature en la respuesta")
                print("\n📄 Respuesta completa:")
                print(json.dumps(order, indent=2)[:500])
                
        else:
            print(f"\n❌ ERROR: Status {response.status_code}")
            print(f"Respuesta: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar al backend")
        print("   Verifica que el servidor esté corriendo en localhost:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_crear_orden_wompi()
