"""
🧪 PRUEBA COMPLETA DEL SISTEMA (SIN WOMPI)
==========================================

Este script prueba TODA la funcionalidad menos el pago real con Wompi.
Demuestra que el sistema está 100% funcional.

Requisitos:
- Backend corriendo en localhost:8000
- Frontend corriendo en localhost:81
- Base de datos PostgreSQL activa
"""

import requests
import json
import time
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

API_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:81"

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{text:^70}")
    print(f"{Fore.CYAN}{'='*70}\n")

def print_success(text):
    print(f"{Fore.GREEN}✅ {text}")

def print_error(text):
    print(f"{Fore.RED}❌ {text}")

def print_info(text):
    print(f"{Fore.YELLOW}ℹ️  {text}")

def print_step(number, text):
    print(f"\n{Fore.MAGENTA}[PASO {number}] {text}")

class GasStoreFlowTest:
    def __init__(self):
        self.token = None
        self.created_order_id = None
        self.tracking_code = None
        self.wompi_reference = None
        
    def test_1_health_check(self):
        """Verificar que backend está corriendo"""
        print_step(1, "Verificar Backend")
        try:
            response = requests.get(f"{API_URL}/api/", timeout=5)
            if response.status_code == 200:
                print_success(f"Backend OK - {API_URL}")
                return True
            else:
                print_error(f"Backend respondió con {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print_error(f"Backend no responde: {e}")
            return False
            
    def test_2_get_products(self):
        """Obtener lista de productos"""
        print_step(2, "Obtener Productos")
        try:
            response = requests.get(f"{API_URL}/ecommerce/products/")
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', [])
                print_success(f"Productos obtenidos: {len(products)}")
                
                if products:
                    product = products[0]
                    print_info(f"  Producto: {product.get('name')}")
                    print_info(f"  Precio: ${product.get('price'):,.0f}")
                    print_info(f"  ID: {product.get('id')}")
                    return product.get('id')
                else:
                    print_error("No hay productos en el sistema")
                    return None
            else:
                print_error(f"Error al obtener productos: {response.status_code}")
                return None
        except Exception as e:
            print_error(f"Error: {e}")
            return None
            
    def test_3_create_order_efectivo(self):
        """Crear orden con pago en efectivo (contra entrega)"""
        print_step(3, "Crear Orden - Pago Contra Entrega")
        
        reference = f"TEST-CASH-{int(time.time())}"
        
        order_data = {
            "customer_name": "Cliente Prueba",
            "customer_email": "prueba@gasstore.com",
            "customer_phone": "+57 300 123 4567",
            "shipping_address": "Calle 123 #45-67, Apto 301",
            "city": "Bogotá",
            "department": "Bogotá D.C.",
            "postal_code": "110111",
            "payment_method": "efectivo",  # CONTRA ENTREGA
            "items": [
                {
                    "product_id": 5,  # Ajustar según tu DB
                    "quantity": 2
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{API_URL}/orders",
                json=order_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                data = response.json()
                order = data.get('data', {})
                self.created_order_id = order.get('id')
                self.tracking_code = order.get('tracking_code')
                
                print_success("Orden creada exitosamente")
                print_info(f"  Order ID: {self.created_order_id}")
                print_info(f"  Tracking: {self.tracking_code}")
                print_info(f"  Total: ${order.get('total'):,.0f} COP")
                print_info(f"  Estado: {order.get('status')}")
                print_info(f"  Método: {order.get('payment_method')}")
                return True
            else:
                print_error(f"Error al crear orden: {response.status_code}")
                print_error(f"Respuesta: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Error: {e}")
            return False
            
    def test_4_create_order_wompi(self):
        """Crear orden con método Wompi (simulado)"""
        print_step(4, "Crear Orden - Wompi (Simulado)")
        
        self.wompi_reference = f"GS-{int(time.time())}-{int(time.time() * 1000) % 10000:04d}"
        
        order_data = {
            "customer_name": "Cliente Wompi Test",
            "customer_email": "wompi@gasstore.com",
            "customer_phone": "+57 310 987 6543",
            "shipping_address": "Carrera 7 #12-34",
            "city": "Medellín",
            "department": "Antioquia",
            "postal_code": "050001",
            "payment_method": "wompi",
            "wompi_reference": self.wompi_reference,
            "items": [
                {
                    "product_id": 5,
                    "quantity": 1
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{API_URL}/orders",
                json=order_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                data = response.json()
                order = data.get('data', {})
                wompi_order_id = order.get('id')
                
                print_success("Orden Wompi creada")
                print_info(f"  Order ID: {wompi_order_id}")
                print_info(f"  Tracking: {order.get('tracking_code')}")
                print_info(f"  Referencia Wompi: {self.wompi_reference}")
                print_info(f"  Estado: {order.get('status')}")
                
                # Guardar para prueba de webhook
                self.wompi_order_tracking = order.get('tracking_code')
                return wompi_order_id
            else:
                print_error(f"Error: {response.status_code}")
                print_error(f"Respuesta: {response.text}")
                return None
                
        except Exception as e:
            print_error(f"Error: {e}")
            return None
            
    def test_5_simulate_webhook(self):
        """Simular webhook de Wompi"""
        print_step(5, "Simular Webhook de Wompi")
        
        if not self.wompi_reference:
            print_error("No hay referencia de Wompi para probar")
            return False
            
        webhook_payload = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": f"wompi-test-{int(time.time())}",
                    "reference": self.wompi_reference,
                    "status": "APPROVED",
                    "amount_in_cents": 180000000,  # $1,800,000 COP
                    "customer_email": "wompi@gasstore.com",
                    "payment_method_type": "CARD",
                    "created_at": datetime.now().isoformat()
                }
            },
            "sent_at": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                f"{API_URL}/webhooks/wompi",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print_success("Webhook procesado correctamente")
                print_info(f"  Referencia: {self.wompi_reference}")
                print_info(f"  Estado transacción: APPROVED")
                return True
            else:
                print_error(f"Error en webhook: {response.status_code}")
                print_error(f"Respuesta: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Error: {e}")
            return False
            
    def test_6_verify_order_status(self):
        """Verificar que la orden se actualizó a PAID"""
        print_step(6, "Verificar Actualización de Estado")
        
        if not self.wompi_order_tracking:
            print_error("No hay orden Wompi para verificar")
            return False
            
        try:
            response = requests.get(f"{API_URL}/orders/tracking/{self.wompi_order_tracking}")
            
            if response.status_code == 200:
                data = response.json()
                order = data.get('data', {})
                status = order.get('status')
                
                print_info(f"  Estado actual: {status}")
                
                if status == 'paid':
                    print_success("✅ Orden marcada como PAGADA (webhook funcionó)")
                    return True
                elif status == 'pending':
                    print_error("⚠️ Orden sigue PENDING (webhook no actualizó)")
                    return False
                else:
                    print_info(f"⚠️ Estado inesperado: {status}")
                    return False
            else:
                print_error(f"Error al obtener orden: {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Error: {e}")
            return False
            
    def test_7_get_order_by_tracking(self):
        """Obtener orden por código de rastreo"""
        print_step(7, "Obtener Orden por Tracking Code")
        
        if not self.tracking_code:
            print_error("No hay tracking code para probar")
            return False
            
        try:
            response = requests.get(f"{API_URL}/orders/tracking/{self.tracking_code}")
            
            if response.status_code == 200:
                data = response.json()
                order = data.get('data', {})
                
                print_success(f"Orden obtenida: {self.tracking_code}")
                print_info(f"  Cliente: {order.get('customer_name')}")
                print_info(f"  Email: {order.get('customer_email')}")
                print_info(f"  Total: ${order.get('total'):,.0f}")
                print_info(f"  Estado: {order.get('status')}")
                
                # Verificar items
                items = order.get('items', [])
                print_info(f"  Items: {len(items)} productos")
                
                return True
            else:
                print_error(f"Error: {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def test_8_frontend_accessible(self):
        """Verificar que frontend está accesible"""
        print_step(8, "Verificar Frontend")
        
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                print_success(f"Frontend OK - {FRONTEND_URL}")
                print_info(f"  URL Checkout: {FRONTEND_URL}/checkout")
                print_info(f"  URL Confirmación: {FRONTEND_URL}/orden-confirmada")
                return True
            else:
                print_error(f"Frontend error: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Frontend no accesible: {e}")
            return False

    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print_header("🧪 PRUEBA COMPLETA DEL SISTEMA GASSTORE")
        
        results = []
        
        # Test 1: Health Check
        results.append(("Backend Health", self.test_1_health_check()))
        
        # Test 2: Products
        product_id = self.test_2_get_products()
        results.append(("Obtener Productos", product_id is not None))
        
        # Test 3: Orden Efectivo
        results.append(("Orden Efectivo", self.test_3_create_order_efectivo()))
        
        # Test 4: Orden Wompi
        wompi_order = self.test_4_create_order_wompi()
        results.append(("Orden Wompi", wompi_order is not None))
        
        # Test 5: Webhook
        if wompi_order:
            results.append(("Webhook Wompi", self.test_5_simulate_webhook()))
            
            # Test 6: Verificar estado
            results.append(("Actualización Estado", self.test_6_verify_order_status()))
        
        # Test 7: Tracking
        results.append(("Obtener por Tracking", self.test_7_get_order_by_tracking()))
        
        # Test 8: Frontend
        results.append(("Frontend Accesible", self.test_8_frontend_accessible()))
        
        # Resumen
        print_header("📊 RESUMEN DE PRUEBAS")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = f"{Fore.GREEN}✅ PASS" if result else f"{Fore.RED}❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\n{Fore.CYAN}Total: {passed}/{total} pruebas exitosas")
        
        if passed == total:
            print(f"\n{Fore.GREEN}{'='*70}")
            print(f"{Fore.GREEN}🎉 TODAS LAS PRUEBAS PASARON")
            print(f"{Fore.GREEN}{'='*70}")
            print(f"\n{Fore.YELLOW}El sistema está 100% funcional.")
            print(f"{Fore.YELLOW}Solo falta configurar llaves REALES de Wompi para procesar pagos.")
        else:
            print(f"\n{Fore.RED}{'='*70}")
            print(f"{Fore.RED}⚠️ ALGUNAS PRUEBAS FALLARON")
            print(f"{Fore.RED}{'='*70}")
            
        return passed == total

if __name__ == "__main__":
    tester = GasStoreFlowTest()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n{Fore.CYAN}📝 PRÓXIMOS PASOS:")
        print(f"  1. Crear cuenta en https://comercios.wompi.co")
        print(f"  2. Obtener llaves de API (sandbox)")
        print(f"  3. Actualizar .env con llaves reales")
        print(f"  4. Probar pago real en checkout")
        print(f"  5. Configurar webhook en producción")
