"""
Script de prueba para el flujo completo de Wompi
Ejecutar desde: python scripts/test_wompi_flow.py
"""

import requests
import json
import time
from datetime import datetime
import uuid

# ─── Configuración ────────────────────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000/api"
WOMPI_PUBLIC_KEY = "pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6"

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# ─── Helper Functions ─────────────────────────────────────────────────────────

def print_section(title):
    """Imprime encabezado de sección"""
    print(f"\n{BLUE}{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}ℹ {msg}{RESET}")

def generate_reference():
    """Genera referencia única para la orden"""
    timestamp = int(time.time())
    random_id = str(uuid.uuid4())[:8].upper()
    return f"TEST-{timestamp}-{random_id}"

# ─── Prueba 1: Crear Orden con Pago Contra Entrega ───────────────────────────

def test_cash_order():
    print_section("PRUEBA 1: Orden con Pago Contra Entrega")
    
    # Obtener productos disponibles
    print_info("Obteniendo productos disponibles...")
    response = requests.get(f"{API_BASE_URL}/products", params={"is_available": "true"})
    
    if response.status_code != 200:
        print_error(f"Error al obtener productos: {response.status_code}")
        return None
    
    products = response.json().get('data', [])
    if not products:
        print_error("No hay productos disponibles")
        return None
    
    product = products[0]
    print_success(f"Producto seleccionado: {product['name']} - ${product['price']:,.0f}")
    
    # Crear orden
    reference = generate_reference()
    order_data = {
        "customer_name": "Juan Pérez Test",
        "customer_email": "test@gasstore.com",
        "customer_phone": "+57 300 123 4567",
        "shipping_address": "Calle 123 #45-67, Apto 101",
        "city": "Bogotá",
        "department": "Bogotá D.C.",
        "postal_code": "110111",
        "payment_method": "cash",
        "wompi_reference": reference,
        "notes": "Orden de prueba - Contra entrega",
        "items": [
            {
                "product_id": product['id'],
                "quantity": 1
            }
        ]
    }
    
    print_info(f"Creando orden con referencia: {reference}")
    response = requests.post(f"{API_BASE_URL}/orders", json=order_data)
    
    if response.status_code != 201:
        print_error(f"Error al crear orden: {response.status_code}")
        print_error(f"Respuesta: {response.text}")
        return None
    
    order = response.json().get('data')
    print_success(f"Orden creada exitosamente")
    print_success(f"  - ID: {order['id']}")
    print_success(f"  - Número: {order['order_number']}")
    print_success(f"  - Tracking: {order['tracking_code']}")
    print_success(f"  - Estado: {order['status']}")
    print_success(f"  - Total: ${float(order['total']):,.0f}")
    
    # Verificar tracking
    print_info("Verificando tracking...")
    response = requests.get(f"{API_BASE_URL}/orders/tracking/{order['tracking_code']}")
    
    if response.status_code == 200:
        print_success("Tracking funciona correctamente")
        tracking_data = response.json().get('data')
        print_success(f"  - Eventos: {len(tracking_data.get('tracking_history', []))}")
    else:
        print_error(f"Error en tracking: {response.status_code}")
    
    return order

# ─── Prueba 2: Crear Orden con Wompi ─────────────────────────────────────────

def test_wompi_order():
    print_section("PRUEBA 2: Orden con Pago Wompi")
    
    # Obtener productos disponibles
    print_info("Obteniendo productos disponibles...")
    response = requests.get(f"{API_BASE_URL}/products", params={"is_available": "true"})
    
    if response.status_code != 200:
        print_error(f"Error al obtener productos: {response.status_code}")
        return None
    
    products = response.json().get('data', [])
    if not products:
        print_error("No hay productos disponibles")
        return None
    
    product = products[0]
    print_success(f"Producto seleccionado: {product['name']} - ${product['price']:,.0f}")
    
    # Crear orden
    reference = generate_reference()
    order_data = {
        "customer_name": "María García Test",
        "customer_email": "maria@gasstore.com",
        "customer_phone": "+57 310 987 6543",
        "shipping_address": "Carrera 45 #67-89",
        "city": "Medellín",
        "department": "Antioquia",
        "postal_code": "050001",
        "payment_method": "wompi",
        "wompi_reference": reference,
        "notes": "Orden de prueba - Wompi",
        "items": [
            {
                "product_id": product['id'],
                "quantity": 2
            }
        ]
    }
    
    print_info(f"Creando orden con referencia: {reference}")
    response = requests.post(f"{API_BASE_URL}/orders", json=order_data)
    
    if response.status_code != 201:
        print_error(f"Error al crear orden: {response.status_code}")
        print_error(f"Respuesta: {response.text}")
        return None
    
    order = response.json().get('data')
    print_success(f"Orden creada exitosamente")
    print_success(f"  - ID: {order['id']}")
    print_success(f"  - Número: {order['order_number']}")
    print_success(f"  - Tracking: {order['tracking_code']}")
    print_success(f"  - Estado: {order['status']} (debe ser 'pending')")
    print_success(f"  - Total: ${float(order['total']):,.0f}")
    print_success(f"  - Referencia Wompi: {order.get('wompi_reference', 'N/A')}")
    
    # Generar URL de Wompi
    total_cents = int(float(order['total']) * 100)
    wompi_url = (
        f"https://checkout.wompi.co/p/"
        f"?public-key={WOMPI_PUBLIC_KEY}"
        f"&currency=COP"
        f"&amount-in-cents={total_cents}"
        f"&reference={reference}"
        f"&redirect-url=http://localhost:81/orden-confirmada?tracking={order['tracking_code']}"
    )
    
    print_info("\n" + "─" * 80)
    print_info("URL de Checkout Wompi:")
    print(f"{YELLOW}{wompi_url}{RESET}")
    print_info("─" * 80)
    print_info("\nAbre esta URL en el navegador para completar el pago de prueba")
    print_info("Usa la tarjeta de prueba: 4242 4242 4242 4242")
    print_info("Vencimiento: 12/25, CVC: 123")
    
    return order

# ─── Prueba 3: Simular Webhook de Wompi ──────────────────────────────────────

def test_wompi_webhook(order_reference):
    print_section("PRUEBA 3: Webhook de Wompi")
    
    if not order_reference:
        print_error("Se requiere una orden de Wompi para probar el webhook")
        return
    
    # Simular webhook de aprobación
    webhook_payload = {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": f"test-tx-{int(time.time())}",
                "amount_in_cents": 5000000,
                "reference": order_reference,
                "customer_email": "maria@gasstore.com",
                "currency": "COP",
                "payment_method_type": "CARD",
                "status": "APPROVED",
                "status_message": None,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "finalized_at": datetime.utcnow().isoformat() + "Z"
            }
        },
        "sent_at": datetime.utcnow().isoformat() + "Z"
    }
    
    print_info("Enviando webhook de pago aprobado...")
    print_info(f"Referencia: {order_reference}")
    
    response = requests.post(
        f"{API_BASE_URL}/webhooks/wompi",
        json=webhook_payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print_success("Webhook procesado exitosamente")
        print_success(f"Respuesta: {response.json()}")
    else:
        print_error(f"Error en webhook: {response.status_code}")
        print_error(f"Respuesta: {response.text}")
        return
    
    # Verificar que la orden se actualizó
    time.sleep(1)  # Esperar un segundo
    
    print_info("Verificando actualización de orden...")
    # Buscar la orden por referencia
    response = requests.get(f"{API_BASE_URL}/admin/orders", params={"search": order_reference})
    
    if response.status_code == 200:
        orders = response.json().get('data', [])
        if orders:
            order = orders[0]
            if order['status'] == 'paid':
                print_success(f"Estado actualizado a: {order['status']}")
                print_success(f"Transaction ID: {order.get('wompi_transaction_id', 'N/A')}")
            else:
                print_error(f"Estado no cambió: {order['status']} (se esperaba 'paid')")
        else:
            print_error("Orden no encontrada")
    else:
        print_error(f"Error al verificar orden: {response.status_code}")

# ─── Prueba 4: Verificar Estados de Orden ────────────────────────────────────

def test_order_statuses():
    print_section("PRUEBA 4: Estados Posibles de Orden")
    
    # Obtener todas las órdenes recientes
    print_info("Obteniendo órdenes recientes...")
    response = requests.get(f"{API_BASE_URL}/admin/orders", params={"page_size": 10})
    
    if response.status_code != 200:
        print_error(f"Error al obtener órdenes: {response.status_code}")
        return
    
    orders = response.json().get('data', [])
    
    if not orders:
        print_info("No hay órdenes para mostrar")
        return
    
    print_success(f"Se encontraron {len(orders)} órdenes recientes:\n")
    
    # Agrupar por estado
    by_status = {}
    for order in orders:
        status = order['status']
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(order)
    
    # Mostrar resumen
    for status, orders_list in by_status.items():
        print(f"  {YELLOW}{status.upper()}{RESET}: {len(orders_list)} órdenes")
        for order in orders_list[:3]:  # Mostrar máximo 3
            print(f"    - {order['order_number']} | {order['payment_method']} | ${float(order['total']):,.0f}")

# ─── Prueba 5: Flujo Completo End-to-End ─────────────────────────────────────

def test_complete_flow():
    print_section("PRUEBA 5: Flujo Completo End-to-End")
    
    print_info("Ejecutando flujo completo de Wompi...")
    
    # 1. Crear orden Wompi
    print("\n1️⃣ Creando orden con método Wompi...")
    order = test_wompi_order()
    
    if not order:
        print_error("No se pudo crear la orden, abortando flujo")
        return
    
    time.sleep(2)
    
    # 2. Simular pago en Wompi
    print("\n2️⃣ Simulando pago en Wompi...")
    print_info("En un escenario real, el usuario pagaría en checkout.wompi.co")
    print_info("Aquí simulamos directamente el webhook de confirmación")
    
    time.sleep(1)
    
    # 3. Webhook de confirmación
    print("\n3️⃣ Procesando webhook de Wompi...")
    test_wompi_webhook(order.get('wompi_reference'))
    
    time.sleep(2)
    
    # 4. Verificar estado final
    print("\n4️⃣ Verificando estado final de la orden...")
    response = requests.get(f"{API_BASE_URL}/orders/tracking/{order['tracking_code']}")
    
    if response.status_code == 200:
        final_order = response.json().get('data')
        print_success("Orden verificada exitosamente")
        print_success(f"  - Número: {final_order['order_number']}")
        print_success(f"  - Estado: {final_order['status']}")
        print_success(f"  - Método de pago: {final_order['payment_method']}")
        print_success(f"  - Eventos de tracking: {len(final_order['tracking_history'])}")
        
        # Mostrar timeline
        print_info("\nTimeline de la orden:")
        for event in final_order['tracking_history']:
            timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            print(f"  {timestamp.strftime('%H:%M:%S')} | {event['status']} | {event['description']}")
    else:
        print_error(f"Error al verificar orden: {response.status_code}")
    
    print_section("FLUJO COMPLETO FINALIZADO")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BLUE}╔{'═'*78}╗")
    print(f"║{' '*26}PRUEBAS DE WOMPI{' '*34}║")
    print(f"║{' '*78}║")
    print(f"║  Configuración:{' '*62}║")
    print(f"║    - API Base: {API_BASE_URL:<59}║")
    print(f"║    - Wompi Key: {WOMPI_PUBLIC_KEY:<57}║")
    print(f"╚{'═'*78}╝{RESET}\n")
    
    # Verificar conectividad con API
    print_info("Verificando conectividad con la API...")
    try:
        response = requests.get(f"{API_BASE_URL}/products", timeout=5)
        if response.status_code == 200:
            print_success("API accesible")
        else:
            print_error(f"API respondió con código {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print_error(f"No se puede conectar a la API: {e}")
        print_error("Asegúrate de que el backend esté corriendo en http://localhost:8000")
        return
    
    # Menú de opciones
    while True:
        print(f"\n{YELLOW}{'─'*80}")
        print("MENÚ DE PRUEBAS")
        print("─"*80 + RESET)
        print("1. Probar orden con pago contra entrega")
        print("2. Probar orden con Wompi (manual)")
        print("3. Simular webhook de Wompi")
        print("4. Ver estados de órdenes")
        print("5. Ejecutar flujo completo (automático)")
        print("0. Salir")
        print(f"{YELLOW}{'─'*80}{RESET}")
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == "1":
            test_cash_order()
        elif choice == "2":
            test_wompi_order()
        elif choice == "3":
            ref = input("Ingresa la referencia de la orden (ej: TEST-1234567890-ABC12): ").strip()
            if ref:
                test_wompi_webhook(ref)
            else:
                print_error("Referencia inválida")
        elif choice == "4":
            test_order_statuses()
        elif choice == "5":
            test_complete_flow()
        elif choice == "0":
            print_info("Saliendo...")
            break
        else:
            print_error("Opción inválida")

if __name__ == "__main__":
    main()
