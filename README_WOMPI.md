# Integración de Pasarela de Pago Wompi 💳

Documentación completa de la integración de Wompi para el e-commerce de GasStore.

## 📚 Índice

1. [Resumen](#resumen)
2. [Arquitectura](#arquitectura)
3. [Configuración](#configuración)
4. [Flujo de Pago](#flujo-de-pago)
5. [Archivos Modificados](#archivos-modificados)
6. [Pruebas](#pruebas)
7. [Despliegue a Producción](#despliegue-a-producción)
8. [Troubleshooting](#troubleshooting)

---

## Resumen

La integración de Wompi permite procesar pagos en línea directamente desde el e-commerce sin necesidad de salir de la página. Los usuarios pueden pagar con:

- **Tarjetas de Crédito/Débito** (Visa, Mastercard, Amex)
- **PSE** (Transferencia bancaria)
- **Nequi**
- **Bancolombia**
- **Otras billeteras digitales**

### Características Implementadas

✅ **Checkout integrado** - Widget de Wompi embebido en la página  
✅ **Pago contra entrega** - Opción alternativa de pago en efectivo  
✅ **Webhook automático** - Actualización de estado en tiempo real  
✅ **Página de confirmación** - UX mejorada post-pago  
✅ **Tracking de pedidos** - Seguimiento completo del estado  
✅ **Pruebas automatizadas** - Script para validar el flujo completo  

---

## Arquitectura

### Componentes del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Vite)                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ CheckoutPage │─▶│ WompiWidget  │─▶│ OrderConfirmation   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                  │                     ▲               │
│         │                  │                     │               │
│         ▼                  ▼                     │               │
│  ┌──────────────────────────────────────────────┘               │
│  │         ordersService (API Client)                           │
│  └──────────────────────────────────────────────────────────────┘
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │ HTTP
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (Django + PostgreSQL)              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ OrderViews   │  │ WompiWebhook │  │ Order Model          │  │
│  │ (API)        │  │ (API)        │  │ + TrackingEvents     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ Webhook (POST)
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                       WOMPI CHECKOUT                             │
├─────────────────────────────────────────────────────────────────┤
│  Usuario completa pago en checkout.wompi.co                     │
│  - Ingresa datos de tarjeta / selecciona PSE / Nequi            │
│  - Wompi procesa transacción                                    │
│  - Wompi envía webhook a backend                                │
│  - Wompi redirige a /orden-confirmada                           │
└─────────────────────────────────────────────────────────────────┘
```

### Base de Datos

**Tabla: ecommerce_order**
```sql
- id (integer)
- order_number (varchar) - Ej: ORD-00001
- tracking_code (uuid) - Para seguimiento público
- status (varchar) - pending, paid, preparing, shipping, delivered, cancelled
- payment_method (varchar) - wompi, cash
- wompi_reference (varchar) - Referencia única para Wompi
- wompi_transaction_id (varchar) - ID de transacción de Wompi
- customer_name, customer_email, customer_phone
- shipping_address, city, department, postal_code
- subtotal, shipping_cost, total
- created_at, updated_at
```

**Tabla: ecommerce_trackingevent**
```sql
- id (integer)
- order_id (foreign key)
- status (varchar)
- description (text)
- location (varchar)
- timestamp (datetime)
```

---

## Configuración

### Variables de Entorno

#### Frontend (`frontend_U/.env`)
```env
VITE_API_URL=http://localhost:8000/api
VITE_WOMPI_PUBLIC_KEY=pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6
VITE_WOMPI_REDIRECT_URL=http://localhost:81/orden-confirmada
```

#### Backend (`.env`)
```env
# Wompi Sandbox
WOMPI_PUBLIC_KEY=pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6
WOMPI_PRIVATE_KEY=${WOMPI_PRIVATE_KEY}_PRIVATE_KEY
WOMPI_EVENTS_SECRET=YOUR_EVENTS_SECRET
WOMPI_INTEGRITY_SECRET=YOUR_INTEGRITY_SECRET

# Para producción, cambiar a llaves reales:
# WOMPI_PUBLIC_KEY=pub_prod_...
# WOMPI_PRIVATE_KEY=prv_prod_...
```

### Dashboard de Wompi

1. Crear cuenta en [comercios.wompi.co](https://comercios.wompi.co)
2. Obtener llaves de sandbox para pruebas
3. Configurar webhook URL:
   - **Sandbox:** `http://YOUR_NGROK_URL/api/webhooks/wompi`
   - **Producción:** `https://imporgasjj.com/api/webhooks/wompi`
4. Activar eventos: `transaction.updated`

---

## Flujo de Pago

### Flujo Completo (Wompi)

```
1. Usuario agrega productos al carrito
   ↓
2. Usuario va a /checkout
   ↓
3. Usuario llena formulario de envío
   ↓
4. Usuario selecciona "Pago con Wompi"
   ↓
5. Usuario hace clic en "Pagar con Wompi"
   ↓
6. Frontend crea orden en backend (status: PENDING)
   ├─ POST /api/orders
   ├─ payload: { customer_name, email, items[], payment_method: 'wompi' }
   └─ response: { order_number, tracking_code, wompi_reference }
   ↓
7. Frontend redirige a Wompi Checkout
   ├─ URL: https://checkout.wompi.co/p/
   ├─ params: public-key, amount-in-cents, reference, redirect-url
   └─ Usuario completa pago en Wompi
   ↓
8. Wompi procesa transacción
   ├─ Si aprueba: status = APPROVED
   └─ Si rechaza: status = DECLINED
   ↓
9. Wompi envía webhook a backend
   ├─ POST /api/webhooks/wompi
   ├─ payload: { event, data: { transaction: { status, reference, id } } }
   └─ Backend actualiza orden según status
   ↓
10. Wompi redirige a /orden-confirmada
    ├─ URL: /orden-confirmada?tracking=<UUID>&id=<reference>
    └─ Frontend muestra página de confirmación
    ↓
11. Usuario ve estado de su pedido
    └─ Puede hacer tracking en /seguimiento-pedido
```

### Flujo Alternativo (Contra Entrega)

```
1-4. (mismo flujo hasta selección de método)
   ↓
5. Usuario selecciona "Pago Contra Entrega"
   ↓
6. Frontend crea orden (status: PENDING, payment_method: 'cash')
   ↓
7. Frontend redirige a /orden-confirmada
   ↓
8. Usuario ve confirmación
   └─ Pago se realizará al recibir el pedido
```

---

## Archivos Modificados

### Frontend (frontend_U)

#### Nuevos Archivos

1. **`src/app/pages/OrderConfirmationPage.tsx`** ✨
   - Página de confirmación post-pago
   - Muestra detalles de la orden
   - Botones de navegación (Rastrear / Seguir Comprando)

2. **`.env`** ✨
   - Variables de entorno de Wompi
   - URL de API del backend

#### Archivos Modificados

1. **`src/app/pages/CheckoutPage.tsx`**
   - ✅ Agregado flujo de Wompi
   - ✅ Creación de orden antes de redirección
   - ✅ Widget de Wompi dinámico
   - ✅ Manejo de estados de pago
   - ✅ Redirección a página de confirmación

2. **`src/App.tsx`**
   - ✅ Ruta `/orden-confirmada` agregada
   - ✅ Import de OrderConfirmationPage

3. **`src/services/orders.ts`**
   - ✅ Método `getAll()` para consultar órdenes
   - ✅ Paginación de resultados

### Backend (BACKEND)

#### Archivos Existentes (ya implementados)

1. **`ecommerce/models.py`**
   - ✅ Modelo Order con campos Wompi
   - ✅ Campos: wompi_reference, wompi_transaction_id

2. **`ecommerce/views.py`**
   - ✅ Vista OrderListView (crear órdenes)
   - ✅ Vista WompiWebhookView (recibir webhooks)
   - ✅ Lógica de actualización de estado

3. **`ecommerce/urls.py`**
   - ✅ Ruta `/webhooks/wompi`

### Documentación

1. **`PRUEBAS_WOMPI.md`** ✨
   - Guía completa de pruebas
   - Casos de uso
   - Tarjetas de prueba
   - Troubleshooting

2. **`BACKEND/scripts/test_wompi_flow.py`** ✨
   - Script automatizado de pruebas
   - Menú interactivo
   - 5 escenarios de prueba

3. **`README_WOMPI.md`** ✨ (este archivo)
   - Documentación completa de integración

### Variables de Entorno

1. **`.env`** (raíz)
   - ✅ WOMPI_PUBLIC_KEY
   - ✅ WOMPI_PRIVATE_KEY (placeholder)
   - ✅ WOMPI_EVENTS_SECRET (placeholder)
   - ✅ WOMPI_INTEGRITY_SECRET (placeholder)

---

## Pruebas

### Pruebas Manuales

Ver [PRUEBAS_WOMPI.md](./PRUEBAS_WOMPI.md) para guía detallada.

#### Tarjetas de Prueba

| Tarjeta | Número | Resultado |
|---------|--------|-----------|
| Visa aprobada | `4242 4242 4242 4242` | APPROVED |
| Mastercard aprobada | `5555 5555 5555 4444` | APPROVED |
| Visa rechazada | `4000 0000 0000 0002` | DECLINED |

**Datos adicionales:**
- Vencimiento: cualquier fecha futura (ej: 12/25)
- CVC: cualquier 3 dígitos (ej: 123)
- Nombre: cualquier texto

### Script de Pruebas Automatizado

```bash
cd BACKEND
python scripts/test_wompi_flow.py
```

**Opciones del menú:**
1. Probar orden con pago contra entrega
2. Probar orden con Wompi (manual)
3. Simular webhook de Wompi
4. Ver estados de órdenes
5. Ejecutar flujo completo (automático)

### Verificación de Base de Datos

```bash
# Conectarse a postgres
docker exec -it postgres psql -U postgres -d imporgas_db

# Ver órdenes recientes
SELECT id, order_number, status, payment_method, total, customer_name 
FROM ecommerce_order 
ORDER BY created_at DESC 
LIMIT 5;

# Ver eventos de tracking
SELECT o.order_number, te.status, te.description, te.timestamp
FROM ecommerce_trackingevent te
JOIN ecommerce_order o ON te.order_id = o.id
ORDER BY te.timestamp DESC
LIMIT 10;
```

---

## Despliegue a Producción

### Checklist Pre-Despliegue

- [ ] Cambiar llaves de sandbox a producción
- [ ] Configurar webhook URL en dashboard de Wompi
- [ ] Implementar firma HMAC para validar webhooks
- [ ] Habilitar HTTPS en toda la aplicación
- [ ] Configurar CORS correctamente
- [ ] Configurar emails transaccionales
- [ ] Probar flujo completo en staging
- [ ] Documentar proceso de rollback

### Llaves de Producción

```env
# Reemplazar en .env
WOMPI_PUBLIC_KEY=pub_prod_XXXXXXXXXXXXXXXXX
WOMPI_PRIVATE_KEY=prv_prod_XXXXXXXXXXXXXXXXX
WOMPI_EVENTS_SECRET=prod_events_XXXXXXXXXXXX
WOMPI_INTEGRITY_SECRET=prod_integrity_XXXXXXXX
```

### Webhook URL Producción

Configurar en dashboard de Wompi:
```
https://imporgasjj.com/api/webhooks/wompi
```

### Implementar Validación HMAC

```python
# En ecommerce/views.py - WompiWebhookView

import hmac
import hashlib
from django.conf import settings

def post(self, request):
    # Obtener firma del header
    signature = request.headers.get('X-Event-Checksum', '')
    
    # Obtener payload
    payload = json.dumps(request.data, separators=(',', ':'))
    
    # Verificar firma
    secret = settings.WOMPI_EVENTS_SECRET
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        return Response({'error': 'Invalid signature'}, status=403)
    
    # Continuar con lógica normal...
```

### Monitoreo

1. **Logs de transacciones**
   - Configurar logging en Django
   - Almacenar eventos de webhook
   - Alertas para pagos fallidos

2. **Métricas**
   - Tasa de conversión
   - Pagos aprobados vs rechazados
   - Tiempo promedio de procesamiento

3. **Dashboard**
   - Panel de órdenes en admin
   - Vista de pagos pendientes
   - Reporte de transacciones

---

## Troubleshooting

### Problema: Orden no se actualiza después de pago

**Síntomas:**
- Usuario paga en Wompi
- Orden queda en estado `PENDING`
- No se crea tracking event de pago

**Causas posibles:**
1. Webhook no está recibiendo notificaciones
2. URL del webhook incorrecta
3. Backend no accesible desde Wompi

**Solución:**
```bash
# 1. Verificar URL del webhook en dashboard de Wompi
# 2. Para desarrollo local, usar ngrok
ngrok http 8000

# 3. Actualizar URL en Wompi dashboard
# https://XXXXX.ngrok.io/api/webhooks/wompi

# 4. Verificar logs del backend
docker logs backend -f | grep -i wompi

# 5. Simular webhook manualmente
curl -X POST http://localhost:8000/api/webhooks/wompi \
  -H "Content-Type: application/json" \
  -d '{"event":"transaction.updated","data":{"transaction":{"reference":"GS-XXX","status":"APPROVED","id":"test"}}}'
```

---

### Problema: Monto incorrecto en Wompi

**Síntomas:**
- Wompi muestra un monto diferente al esperado

**Causa:**
- No se multiplica el monto por 100 (centavos)

**Solución:**
```typescript
// En CheckoutPage.tsx
const total = subtotal + shipping  // Ej: 50000 (pesos)
const amountInCents = total * 100  // Ej: 5000000 (centavos)
```

---

### Problema: Redirección después de pago falla

**Síntomas:**
- Después de pagar, el usuario no regresa a la app
- Página 404 o error

**Causa:**
- URL de redirección incorrecta

**Solución:**
```typescript
// Verificar redirect-url en CheckoutPage.tsx
const redirectUrl = `${window.location.origin}/orden-confirmada?tracking=${order.tracking_code}&id=${reference}`

// Debe ser algo como:
// http://localhost:81/orden-confirmada?tracking=uuid-here&id=GS-xxx
```

---

### Problema: CORS en webhook

**Síntomas:**
- Error CORS en logs
- Webhook retorna 403

**Solución:**
```python
# En settings.py
CORS_ALLOWED_ORIGINS = [
    'https://checkout.wompi.co',
    'http://localhost:81',
]

CSRF_TRUSTED_ORIGINS = [
    'https://checkout.wompi.co',
]
```

---

## Troubleshooting

### Error 422: merchants/undefined

**Síntomas:**
```
api.wompi.co/v1/merchants/undefined:1 Failed to load resource: 422
Error during initialization
POST https://api-sandbox.wompi.co/v1/transactions 422
```

**Causa:** La llave pública de Wompi es **inválida** o **no existe**.

**Solución:**

1. **Verificar llave en `.env`:**
   ```env
   VITE_WOMPI_PUBLIC_KEY=pub_test_XXXXXX  # Debe ser una llave válida
   ```

2. **Obtener llave real:**
   - Crear cuenta en https://comercios.wompi.co/registro
   - Completar KYC (1-3 días hábiles)
   - Ir a Dashboard > Configuración > API Keys
   - Copiar **Public Key Sandbox**

3. **Actualizar configuración:**
   ```bash
   # Editar frontend_U/.env
   VITE_WOMPI_PUBLIC_KEY=pub_test_TU_LLAVE_REAL
   
   # Reiniciar frontend
   cd frontend_U
   npm run dev
   ```

4. **Validar:**
   - Abrir http://localhost:81/checkout
   - Agregar producto al carrito
   - Click "Pagar con Wompi"
   - Checkout debe cargar **sin errores 422** ✅

**Referencia:** Ver [GUIA_RAPIDA_WOMPI.md](GUIA_RAPIDA_WOMPI.md) para pasos detallados.

---

### Error 403: CloudFront

**Síntomas:**
```
403 Forbidden - CloudFront
Request blocked by WAF
```

**Causa:** Wompi bloquea URLs con `localhost` en el parámetro `redirect-url`.

**Solución:** El código ya incluye lógica para omitir `redirect-url` en desarrollo:

```typescript
// CheckoutPage.tsx
const origin = window.location.hostname
const isLocalhost = origin === 'localhost' || origin === '127.0.0.1'

if (!isLocalhost) {
  params.set('redirect-url', redirectUrl)
}
```

✅ **No requiere acción** - ya implementado.

---

### Webhook no se recibe

**Síntomas:**
- Pago aprobado en Wompi
- Orden sigue en estado `pending`
- No se actualiza a `paid`

**Diagnóstico:**

1. **Verificar URL del webhook en Wompi:**
   - Dashboard > Configuración > Webhooks
   - URL: `https://imporgasjj.com/webhooks/wompi`
   - ⚠️ En localhost, Wompi NO puede enviar webhooks

2. **Probar webhook manualmente:**
   ```bash
   curl -X POST http://localhost:8000/webhooks/wompi \
     -H "Content-Type: application/json" \
     -d '{
       "event": "transaction.updated",
       "data": {
         "transaction": {
           "id": "test-123",
           "reference": "GS-1234567890-ABC",
           "status": "APPROVED",
           "amount_in_cents": 180000000
         }
       }
     }'
   ```

3. **Revisar logs del backend:**
   ```bash
   docker logs backend -f --tail=50
   ```

**Solución:**
- En desarrollo: Simular webhook manualmente (ver script `test_sistema_completo.py`)
- En producción: Configurar dominio público y SSL

---

### Pago aprobado pero orden no actualiza

**Verificar referencia coincide:**

```sql
-- En PostgreSQL
SELECT id, order_number, wompi_reference, status, payment_method
FROM ecommerce_order
WHERE wompi_reference = 'GS-1234567890-ABC';
```

**Verificar webhook endpoint:**

```python
# BACKEND/crmChat/views.py (o donde esté el webhook)
@api_view(['POST'])
def wompi_webhook(request):
    data = request.data
    reference = data['data']['transaction']['reference']
    status = data['data']['transaction']['status']
    
    # Buscar orden por referencia
    order = Order.objects.filter(wompi_reference=reference).first()
    
    if order and status == 'APPROVED':
        order.status = 'paid'
        order.save()
        
        # Enviar email confirmación
        send_confirmation_email(order)
        
        return Response({'status': 'ok'})
```

---

### Carrito se vacía antes de pagar

**Síntoma:** Al hacer click en "Pagar con Wompi", el carrito se vacía y muestra mensaje de carrito vacío.

**Solución:** Ya implementado con `isProcessingWompi` state:

```typescript
// CheckoutPage.tsx
const [isProcessingWompi, setIsProcessingWompi] = useState(false)

// Al iniciar pago
setIsProcessingWompi(true)

// No limpiar carrito hasta después de regresar de Wompi
// El cart se limpia en OrderConfirmationPage
```

✅ **Ya solucionado** - no requiere acción.

---

### Tarjeta de prueba rechazada en sandbox

**Tarjetas válidas para sandbox:**

| Tarjeta | Resultado |
|---------|-----------|
| `4242 4242 4242 4242` | ✅ APROBADO |
| `4111 1111 1111 1111` | ✅ APROBADO |
| `5555 5555 5555 4444` | ✅ APROBADO (Mastercard) |
| `4000 0000 0000 0002` | ❌ RECHAZADO (Fondos) |

**Datos adicionales:**
- CVV: `123`
- Fecha: Cualquier futura (ej: `12/25`)
- Titular: Cualquier nombre

---

## Recursos

### Documentación Oficial

- [Wompi Docs](https://docs.wompi.co)
- [Checkout Widget](https://docs.wompi.co/docs/en/checkout-widget)
- [Webhooks](https://docs.wompi.co/docs/en/webhooks)
- [Dashboard](https://comercios.wompi.co)

### Soporte

- Email: soporte@wompi.co
- Chat en dashboard de comercios

### Testing

- [Tarjetas de prueba](https://docs.wompi.co/docs/en/test-cards)
- [Cuentas bancarias de prueba](https://docs.wompi.co/docs/en/test-bank-accounts)

---

## Próximos Pasos

### Funcionalidades Pendientes

1. **Integrity Signature**
   - Generar hash SHA-256 de la transacción
   - Incluir en widget para mayor seguridad

2. **Emails Transaccionales**
   - Confirmación de orden (✅ servidor SMTP configurado)
   - Pago aprobado
   - Pedido enviado
   - Pedido entregado

3. **Webhooks Adicionales**
   - `transaction.failed`
   - `transaction.refunded`

4. **Panel de Admin**
   - Dashboard de ventas
   - Órdenes pendientes de pago
   - Reconciliación con Wompi

5. **Pagos Recurrentes**
   - Suscripciones mensuales
   - Planes de mantenimiento

6. **Reembolsos**
   - Procesar reembolsos desde el admin
   - Webhook de confirmación

---

## Changelog

### v1.0.0 (2025-01-XX)

**Implementado:**
- ✅ Integración completa de Wompi Checkout Widget
- ✅ Flujo de pago contra entrega
- ✅ Webhook para actualización automática de estado
- ✅ Página de confirmación de orden
- ✅ Script de pruebas automatizado
- ✅ Documentación completa

**Backend:**
- ✅ Modelo Order con campos Wompi
- ✅ Vista WompiWebhookView
- ✅ Tracking events automáticos

**Frontend:**
- ✅ CheckoutPage con integración Wompi
- ✅ OrderConfirmationPage
- ✅ Servicio de órdenes actualizado

**Documentación:**
- ✅ PRUEBAS_WOMPI.md
- ✅ README_WOMPI.md
- ✅ Script de pruebas

---

## Licencia

© 2025 GasStore - Todos los derechos reservados

---

## Contacto

Para preguntas sobre la integración de Wompi:
- Email: luissteban999@gmail.com
- Dashboard admin: http://localhost:81/admin

---

**Última actualización:** Enero 2025  
**Versión:** 1.0.0  
**Estado:** ✅ Funcional en Sandbox
