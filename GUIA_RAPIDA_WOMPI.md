# 🚀 GUÍA RÁPIDA: Obtener Llaves de Wompi

## ⚡ 3 Pasos para Solucionar el Error 422

### PASO 1: Crear Cuenta en Wompi (10 minutos)

**1.1 Ir al registro:**
```
https://comercios.wompi.co/registro
```

**1.2 Llenar formulario:**
```
Nombre del comercio: IMPORGAS JJ SAS
Email: [tu email corporativo]
Teléfono: [número de contacto]
País: Colombia
NIT/RUT: [número de identificación tributaria]
```

**1.3 Verificar email:**
- Revisar bandeja de entrada
- Click en link de verificación
- Crear contraseña

---

### PASO 2: Completar Perfil (15 minutos)

**2.1 Iniciar sesión:**
```
https://comercios.wompi.co/login
```

**2.2 Ir a "Mi Negocio" > "Información Legal":**

Subir documentos:
- ✅ Cámara de Comercio (PDF, max 5MB)
- ✅ RUT (Registro Único Tributario)
- ✅ Cédula del representante legal

**2.3 Configurar cuenta bancaria:**
- Banco
- Tipo de cuenta (Ahorros/Corriente)
- Número de cuenta
- Titular (debe coincidir con RUT)

**2.4 Esperar aprobación:**
- ⏱️ Tiempo estimado: 1-3 días hábiles
- 📧 Recibirás email cuando esté aprobado

---

### PASO 3: Obtener Llaves API (2 minutos)

**Una vez aprobada tu cuenta:**

**3.1 Ir a Dashboard:**
```
https://comercios.wompi.co/dashboard
```

**3.2 Menú lateral > "Configuración" > "API Keys"**

**3.3 Copiar llaves:**

```
🧪 SANDBOX (Pruebas):
Public Key:  pub_test_XXXXXXXXXXXXXXXXXXXXXXX
Private Key: prv_test_XXXXXXXXXXXXXXXXXXXXXXX

🚀 PRODUCTION (Real):
Public Key:  pub_prod_XXXXXXXXXXXXXXXXXXXXXXX
Private Key: prv_prod_XXXXXXXXXXXXXXXXXXXXXXX
```

**⚠️ IMPORTANTE:**
- Usar llaves de **SANDBOX** primero para probar
- Cambiar a **PRODUCTION** solo cuando todo funcione
- **NUNCA** compartir la Private Key

---

## 🔧 Configurar en tu Proyecto

### Actualizar Frontend

**Archivo:** `frontend_U/.env`

```env
# CAMBIAR ESTA LÍNEA:
VITE_WOMPI_PUBLIC_KEY=pub_test_wrhmXXJLZGHgUIqSsdRDhn5XsENolPk6

# POR TU LLAVE REAL:
VITE_WOMPI_PUBLIC_KEY=pub_test_TU_LLAVE_AQUI
```

### Actualizar Backend

**Archivo:** `.env` (raíz del proyecto)

```env
# Agregar estas líneas:
WOMPI_PUBLIC_KEY=pub_test_TU_LLAVE_PUBLICA
WOMPI_PRIVATE_KEY=prv_test_TU_LLAVE_PRIVADA
WOMPI_EVENTS_SECRET=TU_EVENTS_SECRET
```

**Obtener Events Secret:**
- Dashboard Wompi > Configuración > Webhooks
- Copiar "Events Secret"

---

## 🧪 Probar Inmediatamente

### 1. Reiniciar Frontend

```powershell
cd frontend_U
npm run dev
```

### 2. Ir a Checkout

```
http://localhost:81/checkout
```

### 3. Agregar Producto y Pagar

**Datos de prueba:**
```
Email: test@gasstore.com
Nombre: Test Usuario
Teléfono: +57 300 123 4567
Dirección: Calle 123 #45-67
```

### 4. En Wompi - Usar Tarjeta de Prueba

```
💳 Número: 4242 4242 4242 4242
📅 Fecha: 12/25 (cualquier futura)
🔒 CVV: 123
👤 Titular: TEST USER
```

### 5. Verificar

✅ **SIN errores 422** → Llave válida  
✅ Pago se procesa  
✅ Redirige a confirmación  
✅ Orden aparece en "Mis Pedidos"

---

## 🎯 Tarjetas de Prueba en Sandbox

| Tarjeta | Resultado |
|---------|-----------|
| `4242 4242 4242 4242` | ✅ APROBADO |
| `4111 1111 1111 1111` | ✅ APROBADO |
| `5555 5555 5555 4444` | ✅ APROBADO (Mastercard) |
| `4000 0000 0000 0002` | ❌ RECHAZADO (Fondos insuficientes) |
| `4000 0000 0000 0069` | ❌ RECHAZADO (CVV inválido) |

**Todas con:**
- CVV: `123`
- Fecha: Cualquier futura (ej: `12/25`)

---

## ⚠️ Si NO Puedes Crear Cuenta Ahora

### Opción A: Demo de Wompi (Sin Pagos Reales)

```javascript
// Cambiar en CheckoutPage.tsx temporalmente:
window.location.href = 'https://checkout.wompi.co/demo'
```

⚠️ Esto solo muestra la UI, NO procesa pagos.

### Opción B: Usar Pago "Contra Entrega"

Mientras obtienes las llaves, el usuario puede pagar al recibir:

1. En checkout, seleccionar "Contra Entrega"
2. Orden se crea como `pending`
3. Al entregar, marcar como `paid` manualmente

---

## 📞 ¿Problemas al Crear Cuenta?

### Soporte Wompi

- **Email:** soporte@wompi.co
- **Chat:** Desde comercios.wompi.co (esquina inferior derecha)
- **Teléfono:** +57 (1) 5808181
- **Horario:** Lun-Vie 8am-6pm (Colombia)

### Preguntas Frecuentes

**P: ¿Cuánto demora la aprobación?**  
R: 1-3 días hábiles si los documentos están completos.

**P: ¿Qué comisión cobra Wompi?**  
R: ~3.5% + IVA por transacción (varía según acuerdo).

**P: ¿Puedo usar sandbox sin KYC?**  
R: No, necesitas cuenta aprobada incluso para sandbox.

**P: ¿Hay costo por crear cuenta?**  
R: No, es gratis. Solo pagas comisión por transacciones.

**P: ¿Funciona para otros países?**  
R: Wompi opera principalmente en Colombia.

---

## ✅ Checklist

- [ ] Crear cuenta en comercios.wompi.co
- [ ] Verificar email
- [ ] Subir documentos (Cámara Comercio, RUT, Cédula)
- [ ] Configurar cuenta bancaria
- [ ] Esperar aprobación (1-3 días)
- [ ] Obtener llaves sandbox
- [ ] Actualizar `.env` del frontend
- [ ] Actualizar `.env` del backend
- [ ] Reiniciar servicios
- [ ] Probar con tarjeta `4242 4242 4242 4242`
- [ ] Verificar sin errores 422
- [ ] Confirmar orden se crea
- [ ] Validar webhook actualiza estado

---

## 🎉 Resultado Esperado

### Antes (Con Llave Inválida)

```
❌ api.wompi.co/v1/merchants/undefined:1 Failed to load resource: 422
❌ Error during initialization
❌ POST https://api-sandbox.wompi.co/v1/transactions 422
```

### Después (Con Llave Válida)

```
✅ Checkout de Wompi carga perfectamente
✅ Formulario de pago funcional
✅ Transacción se procesa
✅ Webhook actualiza orden a "paid"
✅ Usuario ve confirmación
```

---

## 📚 Documentación Adicional

| Archivo | Descripción |
|---------|-------------|
| `SOLUCION_ERROR_422_WOMPI.md` | Explicación detallada del error |
| `RESUMEN_EJECUTIVO_WOMPI.md` | Estado completo del proyecto |
| `PRUEBAS_WOMPI.md` | Guía de pruebas manuales |
| `README_WOMPI.md` | Documentación técnica completa |
| `scripts/test_sistema_completo.py` | Tests automatizados |

---

**¡Con llaves reales, el sistema funcionará al 100%!** 🚀
