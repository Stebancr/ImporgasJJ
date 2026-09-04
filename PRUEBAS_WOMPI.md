# Pruebas de Pasarela de Pago Wompi

Este documento describe el proceso completo de pruebas para la integración de Wompi en el e-commerce.

## 📋 Configuración Inicial

### 1. Variables de Entorno

**Frontend (frontend_U/.env):**
```env
VITE_API_URL=http://localhost:8000/api
VITE_WOMPI_PUBLIC_KEY=pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6
VITE_WOMPI_REDIRECT_URL=http://localhost:81/orden-confirmada
```

**Backend (.env):**
```env
WOMPI_PUBLIC_KEY=pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6
WOMPI_PRIVATE_KEY=${WOMPI_PRIVATE_KEY}_PRIVATE_KEY
WOMPI_EVENTS_SECRET=YOUR_EVENTS_SECRET
WOMPI_INTEGRITY_SECRET=YOUR_INTEGRITY_SECRET
```

### 2. Credenciales de Sandbox

- **Llave Pública:** `pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6`
- **Ambiente:** Sandbox (pruebas)
- **URL Checkout:** https://checkout.wompi.co/p/
- **URL API:** https://api.payouts.wompi.co/v1

## 🔄 Flujo de Pago Implementado

### Arquitectura del Flujo

```
1. Usuario llena formulario checkout
   ↓
2. Selecciona método de pago (Wompi o Contra Entrega)
   ↓
3a. Si elige Wompi:
   - Frontend crea orden en backend (status: PENDING)
   - Frontend redirige a Wompi Checkout
   - Usuario completa pago en Wompi
   - Wompi redirige a /orden-confirmada
   - Webhook actualiza estado a PAID
   
3b. Si elige Contra Entrega:
   - Frontend crea orden (status: PENDING)
   - Redirige a /orden-confirmada
   - Orden queda pendiente hasta entrega
```

### Componentes Involucrados

#### Frontend
- **CheckoutPage.tsx** - Formulario de checkout con integración Wompi
- **OrderConfirmationPage.tsx** - Página de confirmación post-pago
- **WompiCheckout.tsx** - Componente widget de Wompi
- **ordersService.ts** - Servicio API de órdenes

#### Backend
- **ecommerce/views.py** - Vistas de órdenes y webhook Wompi
- **ecommerce/models.py** - Modelo Order con campos Wompi
- **ecommerce/urls.py** - Rutas incluyendo webhook

## 🧪 Casos de Prueba

### Prueba 1: Pago Contra Entrega

**Objetivo:** Verificar creación de orden sin pasarela de pago

**Pasos:**
1. Iniciar frontend: `cd frontend_U && npm run dev`
2. Agregar producto al carrito
3. Ir a checkout (`/checkout`)
4. Llenar formulario:
   - Nombre: Juan Pérez
   - Email: juan@test.com
   - Teléfono: +57 300 123 4567
   - Dirección: Calle 123 #45-67
   - Ciudad: Bogotá
   - Departamento: Bogotá D.C.
5. Seleccionar "Pago Contra Entrega"
6. Click "Confirmar Pedido"

**Resultado Esperado:**
- ✅ Orden creada con `payment_method: 'cash'`
- ✅ Estado inicial: `PENDING`
- ✅ Redirige a `/orden-confirmada?tracking=<UUID>`
- ✅ Muestra número de orden (ORD-00001)
- ✅ Carrito se vacía
- ✅ Email de confirmación enviado (si SMTP configurado)

**Verificación Backend:**
```bash
# Conectarse a postgres
docker exec -it postgres psql -U postgres -d imporgas_db

# Ver última orden
SELECT id, order_number, status, payment_method, total, customer_name 
FROM ecommerce_order 
ORDER BY created_at DESC 
LIMIT 1;

# Ver tracking events
SELECT status, description, timestamp 
FROM ecommerce_trackingevent 
WHERE order_id = (SELECT id FROM ecommerce_order ORDER BY created_at DESC LIMIT 1);
```

---

### Prueba 2: Pago con Wompi - Flujo Completo

**Objetivo:** Probar integración completa con Wompi desde checkout hasta confirmación

**Pasos:**
1. Agregar producto al carrito (precio mínimo: $10,000 COP)
2. Ir a `/checkout`
3. Llenar formulario de información
4. Seleccionar "Pago con Wompi"
5. Click "Pagar con Wompi"
6. **Frontend crea orden con estado PENDING**
7. **Redirige a checkout.wompi.co**
8. En Wompi, seleccionar método de pago de prueba:
   - **Tarjeta de Crédito:**
     - Número: `4242 4242 4242 4242`
     - Vencimiento: cualquier fecha futura (ej: 12/25)
     - CVC: cualquier 3 dígitos (ej: 123)
   - **Nequi:** usar número de prueba
   - **PSE:** seleccionar banco de prueba
9. Completar pago en Wompi
10. Wompi redirige a `/orden-confirmada?tracking=<UUID>&id=<reference>`

**Resultado Esperado:**
- ✅ Orden creada antes de redirección a Wompi
- ✅ Estado inicial: `PENDING`
- ✅ `wompi_reference` guardado en orden
- ✅ Redirección exitosa a Wompi
- ✅ Pago procesado en Wompi
- ✅ Redirección de vuelta a la app
- ✅ Página de confirmación muestra datos correctos
- ✅ Webhook recibe notificación (ver logs)
- ✅ Estado actualizado a `PAID` (verificar en DB)

**Tarjetas de Prueba Wompi:**

| Tarjeta | Número | Resultado |
|---------|--------|-----------|
| Visa aprobada | 4242 4242 4242 4242 | APPROVED |
| Mastercard aprobada | 5555 5555 5555 4444 | APPROVED |
| Amex aprobada | 3782 822463 10005 | APPROVED |
| Visa rechazada | 4000 0000 0000 0002 | DECLINED |
| Mastercard sin fondos | 5555 5555 5555 5557 | DECLINED |

**Montos de Prueba:**
- Usar montos reales en COP (centavos × 100)
- Ejemplo: $50,000 COP = 5000000 centavos
- Mínimo recomendado: $10,000 COP

---

### Prueba 3: Webhook de Wompi

**Objetivo:** Verificar que el webhook actualiza correctamente el estado de la orden

**Configuración Webhook:**
- URL: `http://localhost:8000/api/webhooks/wompi`
- Para pruebas locales, usar ngrok o similar para exponer puerto

**Simular Webhook Manualmente:**

```bash
# En terminal local
curl -X POST http://localhost:8000/api/webhooks/wompi \
  -H "Content-Type: application/json" \
  -d '{
    "event": "transaction.updated",
    "data": {
      "transaction": {
        "id": "test-tx-001",
        "reference": "GS-1234567890-ABC12",
        "status": "APPROVED",
        "amount_in_cents": 5000000,
        "customer_email": "test@test.com"
      }
    }
  }'
```

**Payload Real de Wompi:**
```json
{
  "event": "transaction.updated",
  "data": {
    "transaction": {
      "id": "25399-1639078700-55333",
      "amount_in_cents": 5000000,
      "reference": "GS-1639078650-XYZ45",
      "customer_email": "juan@test.com",
      "currency": "COP",
      "payment_method_type": "CARD",
      "status": "APPROVED",
      "status_message": null,
      "created_at": "2024-01-15T10:30:00.000Z",
      "finalized_at": "2024-01-15T10:31:00.000Z"
    }
  },
  "sent_at": "2024-01-15T10:31:05.000Z"
}
```

**Estados de Transacción:**
- `APPROVED` - Pago aprobado → Orden cambia a `PAID`
- `DECLINED` - Pago rechazado → Orden cambia a `CANCELLED`
- `PENDING` - En proceso → Orden queda `PENDING`
- `VOIDED` - Anulado → Orden cambia a `CANCELLED`
- `ERROR` - Error → Orden cambia a `CANCELLED`

**Verificación:**
```sql
-- Ver orden actualizada
SELECT id, order_number, status, wompi_transaction_id, wompi_reference
FROM ecommerce_order
WHERE wompi_reference = 'GS-1234567890-ABC12';

-- Ver evento de tracking creado
SELECT status, description, timestamp
FROM ecommerce_trackingevent
WHERE order_id = (
  SELECT id FROM ecommerce_order 
  WHERE wompi_reference = 'GS-1234567890-ABC12'
)
ORDER BY timestamp DESC;
```

---

### Prueba 4: Página de Confirmación

**Objetivo:** Verificar que la página de confirmación muestra información correcta

**Acceso Directo:**
```
http://localhost:81/orden-confirmada?tracking=<UUID>
```

**Datos Mostrados:**
- ✅ Número de orden (ORD-00001)
- ✅ Total pagado
- ✅ Código de seguimiento (primeros 8 caracteres)
- ✅ Método de pago (Wompi o Contra Entrega)
- ✅ Estado del pago
- ✅ Mensaje apropiado según método de pago

**Botones:**
- "Rastrear Pedido" → `/seguimiento-pedido?tracking=<UUID>`
- "Seguir Comprando" → `/productos`

---

### Prueba 5: Seguimiento de Orden

**Objetivo:** Verificar que el usuario puede rastrear su orden

**Pasos:**
1. Desde página de confirmación, click "Rastrear Pedido"
2. O ir directamente a `/seguimiento-pedido?tracking=<UUID>`

**Resultado Esperado:**
- ✅ Muestra timeline de estados
- ✅ Eventos de tracking en orden cronológico
- ✅ Estado actual resaltado
- ✅ Información de envío
- ✅ Lista de productos

---

## 🛠️ Herramientas de Desarrollo

### Logs del Backend

```bash
# Ver logs del contenedor Django
docker logs -f backend --tail=100

# Filtrar por webhook
docker logs backend 2>&1 | grep -i wompi
```

### Inspeccionar Base de Datos

```bash
# Entrar a postgres
docker exec -it postgres psql -U postgres -d imporgas_db

# Órdenes recientes
SELECT 
  id, 
  order_number, 
  status, 
  payment_method, 
  wompi_reference,
  wompi_transaction_id,
  total,
  customer_name,
  created_at
FROM ecommerce_order
ORDER BY created_at DESC
LIMIT 10;

# Items de una orden
SELECT 
  oi.id,
  p.name as product_name,
  oi.quantity,
  oi.unit_price,
  oi.subtotal
FROM ecommerce_orderitem oi
JOIN ecommerce_product p ON oi.product_id = p.id
WHERE oi.order_id = <ORDER_ID>;

# Tracking history
SELECT 
  status,
  description,
  location,
  timestamp
FROM ecommerce_trackingevent
WHERE order_id = <ORDER_ID>
ORDER BY timestamp ASC;
```

### Network Debugging

```bash
# Verificar conectividad con Wompi
curl -I https://checkout.wompi.co

# Probar webhook localmente con ngrok
ngrok http 8000

# Actualizar URL del webhook en Wompi dashboard:
# https://XXXXX.ngrok.io/api/webhooks/wompi
```

---

## 📊 Verificación de Componentes

### CheckoutPage
- [ ] Formulario de información funciona
- [ ] Validación de campos requeridos
- [ ] Selector de método de pago
- [ ] Cálculo correcto de totales
- [ ] Botón Wompi crea orden antes de redirección
- [ ] Botón contra entrega crea orden y redirige
- [ ] Manejo de errores

### OrderConfirmationPage
- [ ] Carga orden por tracking code
- [ ] Muestra información correcta
- [ ] Maneja estado pendiente de pago
- [ ] Maneja pago confirmado
- [ ] Botones de navegación funcionan

### Backend Webhook
- [ ] Recibe POST requests
- [ ] Valida estructura del payload
- [ ] Encuentra orden por referencia
- [ ] Actualiza estado según transacción
- [ ] Crea tracking event
- [ ] Maneja estados: APPROVED, DECLINED, VOIDED, ERROR

### Base de Datos
- [ ] Orden con campos Wompi correctos
- [ ] Tracking events creados
- [ ] Referencias únicas
- [ ] Estados válidos

---

## ⚠️ Problemas Comunes

### 1. Orden no se actualiza después de pago

**Causa:** Webhook no recibe notificación de Wompi

**Solución:**
- Verificar URL del webhook en dashboard de Wompi
- Usar ngrok para exponer localhost
- Verificar logs del backend
- Simular webhook manualmente

### 2. Redirección falla después de pago

**Causa:** URL de redirección incorrecta

**Solución:**
```typescript
// Verificar en CheckoutPage.tsx
const redirectUrl = `${window.location.origin}/orden-confirmada?tracking=${order.tracking_code}&id=${reference}`
```

### 3. Monto incorrecto en Wompi

**Causa:** No se multiplica por 100 (centavos)

**Solución:**
```typescript
const amountInCents = total * 100  // COP en centavos
```

### 4. Referencia duplicada

**Causa:** Regeneración de referencia en cada render

**Solución:**
```typescript
const reference = useMemo(
  () => `GS-${Date.now()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`,
  []  // Array vacío = se genera solo una vez
)
```

### 5. CORS en webhook

**Causa:** Wompi hace POST cross-origin

**Solución:**
```python
# Backend settings.py
CORS_ALLOWED_ORIGINS = [
    'https://checkout.wompi.co',
    'http://localhost:81',
]
```

---

## 🔒 Seguridad

### Producción
- [ ] Usar llaves de producción (no test)
- [ ] Implementar firma HMAC en webhook
- [ ] Validar integrity signature
- [ ] Usar HTTPS para webhook
- [ ] No exponer llaves privadas en frontend

### Validación de Webhook
```python
import hmac
import hashlib

def verify_wompi_signature(payload, signature, secret):
    """Verificar firma HMAC del webhook"""
    computed = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)
```

---

## 📝 Checklist Final

### Pre-Despliegue
- [ ] Variables de entorno configuradas
- [ ] Llaves de sandbox probadas
- [ ] Flujo completo funciona localmente
- [ ] Webhook responde correctamente
- [ ] Emails de confirmación enviados
- [ ] Base de datos registra todo

### Producción
- [ ] Cambiar a llaves de producción
- [ ] Configurar webhook URL pública
- [ ] Implementar validación HMAC
- [ ] Habilitar HTTPS
- [ ] Monitoreo de transacciones
- [ ] Logs de errores
- [ ] Backups de base de datos

---

## 📚 Recursos

### Documentación Wompi
- Dashboard: https://comercios.wompi.co
- Docs API: https://docs.wompi.co
- Checkout Widget: https://docs.wompi.co/docs/en/checkout-widget
- Webhooks: https://docs.wompi.co/docs/en/webhooks

### Soporte
- Email: soporte@wompi.co
- Chat: Desde el dashboard

---

## 🎯 Próximos Pasos

1. **Implementar Integrity Signature**
   - Generar hash SHA-256 de la transacción
   - Incluir en widget de Wompi

2. **Emails Transaccionales**
   - Email de confirmación de orden
   - Email de pago aprobado
   - Email de envío

3. **Panel de Admin**
   - Vista de órdenes pendientes
   - Actualización manual de estado
   - Reembolsos

4. **Reportes**
   - Dashboard de ventas
   - Estado de pagos
   - Reconciliación con Wompi

---

## 📄 Notas Finales

- Este documento debe actualizarse con cada cambio en el flujo
- Documentar nuevos casos de prueba según aparezcan
- Mantener registro de issues y soluciones
- Revisar y actualizar antes de cada release
