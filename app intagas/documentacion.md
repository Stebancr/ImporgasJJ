# Prompt: Desarrollo de Aplicación Móvil para Visitas Técnicas

Actúa como un Arquitecto de Software Senior y un desarrollador Full Stack experto en aplicaciones móviles, UX/UI, React Native (Expo) o Flutter, consumo de APIs REST, autenticación JWT y optimización de rendimiento.

## Contexto del proyecto

Ya existe un **Backend completamente desarrollado** que expone todas las APIs necesarias.

La aplicación móvil **NO almacenará información crítica**, únicamente consumirá las APIs existentes.

Toda la lógica de negocio ya se encuentra implementada en el servidor.

La aplicación debe ser extremadamente ligera, rápida, intuitiva y fácil de utilizar por técnicos de campo.

El administrador NO utilizará la aplicación móvil.

Él trabajará desde el Front Web existente.

La aplicación será únicamente para los técnicos.

---

# Objetivo

Desarrollar una aplicación móvil para técnicos que realizan visitas técnicas a clientes.

El administrador agenda las visitas desde el sistema web.

Cuando el técnico inicia sesión podrá visualizar únicamente las visitas asignadas.

Durante la visita diligenciará un formulario, agregará fotografías como evidencia y enviará toda la información al servidor.

Posteriormente el administrador podrá generar automáticamente un PDF utilizando toda la información diligenciada por el técnico.

El PDF debe tener el mismo formato del informe suministrado como referencia.

---

# Inicio de sesión

La aplicación debe iniciar mostrando un Login.

Debe permitir:

* Correo electrónico o usuario
* Contraseña
* Recordar sesión
* Recuperar contraseña
* Cerrar sesión

La autenticación será mediante JWT utilizando el backend existente.

Debe manejar:

* Refresh Token
* Expiración automática
* Cierre de sesión si el token expira
* Almacenamiento seguro del token (Secure Storage / Keychain)

---

# Flujo de la aplicación

## 1. Login

↓

## 2. Dashboard

Debe mostrar:

* Bienvenida al técnico
* Cantidad de visitas pendientes
* Cantidad de visitas realizadas
* Cantidad de visitas del día
* Botón para sincronizar información

↓

## 3. Lista de visitas

Cada tarjeta debe mostrar:

* Nombre del cliente
* Dirección
* Fecha
* Hora
* Tipo de servicio
* Estado

Estados:

* Pendiente
* En proceso
* Finalizada

Debe permitir buscar y filtrar.

↓

## 4. Detalle de la visita

Debe mostrar toda la información enviada desde el backend:

Datos del cliente

* Nombre
* Teléfono
* Correo
* Dirección

Información de la orden

* Tipo de tarea
* Fecha
* Hora
* Descripción
* Observaciones iniciales

Botón:

"Iniciar visita"

↓

## 5. Formulario técnico

El formulario debe ser dinámico para permitir futuras modificaciones desde el backend.

Debe incluir campos como:

### Información del cliente

Persona que atiende

---

### Equipos a asistir

Ejemplo:

* Estufa
* Horno
* Calentador
* Parrilla
* Otro

---

### Ubicación del equipo

Ejemplo:

* Cocina
* Patio
* Balcón
* Exterior
* Otro

---

### Motivo del servicio

Campo de texto largo.

---

### Solución realizada

Campo de texto largo.

---

### Observaciones

Campo de texto largo.

---

### Recomendaciones

Campo de texto largo.

---

### Valor del servicio

Campo numérico.

---

### Método de pago

* Efectivo
* Transferencia
* Tarjeta
* Otro

---

### Firma del cliente

Debe permitir firmar directamente sobre la pantalla.

Guardar la firma como imagen.

---

# Evidencias fotográficas

El técnico podrá:

Tomar fotografías desde la cámara.

También podrá seleccionar imágenes desde la galería.

Las imágenes deben comprimirse automáticamente antes de enviarlas.

Permitir:

* Vista previa
* Eliminar
* Agregar varias fotografías

Mínimo:

1 fotografía.

Máximo:

20 fotografías.

---

# Envío

Al finalizar:

Botón

"Finalizar visita"

Debe:

Validar todos los campos obligatorios.

Subir fotografías.

Subir firma.

Enviar formulario.

Cambiar el estado de la visita a Finalizada.

Mostrar mensaje de éxito.

---

# Generación del PDF

La aplicación móvil NO genera el PDF.

Únicamente enviará la información al backend.

El administrador desde el sistema web podrá generar el PDF con exactamente el mismo formato del documento de referencia.

---

# Sincronización

La aplicación debe funcionar incluso si el técnico pierde conexión.

Implementar:

* Caché local ligera
* Cola de sincronización
* Reintento automático
* Sincronización manual

Cuando vuelva Internet deberá enviar automáticamente la información pendiente.

---

# Notificaciones

Debe soportar Push Notifications para:

Nueva visita asignada.

Cambio de horario.

Cancelación.

Reprogramación.

---

# Arquitectura recomendada

Si se utiliza React Native:

* Expo
* TypeScript
* React Navigation
* React Query / TanStack Query
* Axios
* React Hook Form
* Zod
* Zustand
* MMKV o AsyncStorage para caché
* SecureStore para credenciales

Si se utiliza Flutter:

Aplicar Clean Architecture con Provider, Riverpod o Bloc.

---

# Diseño

La interfaz debe ser:

Minimalista.

Muy rápida.

Pensada para técnicos.

Botones grandes.

Alto contraste.

Pocos pasos.

Fácil de usar con una sola mano.

Compatible con modo claro y oscuro.

---

# Rendimiento

La aplicación debe:

* Abrir en menos de 2 segundos.
* Consumir poca memoria.
* Minimizar llamadas al backend.
* Comprimir imágenes antes del envío.
* Cargar información de manera progresiva.
* Evitar renderizados innecesarios.
* Funcionar correctamente en dispositivos Android de gama media.

---

# Seguridad

Implementar:

* JWT
* HTTPS
* Validación de certificados
* Almacenamiento seguro de credenciales
* Protección contra manipulación de peticiones
* Manejo de expiración del token
* Cierre automático por inactividad (configurable)

---

# Código

El proyecto debe cumplir con:

* Clean Architecture
* SOLID
* DRY
* KISS
* Separación por capas
* Componentes reutilizables
* Código completamente documentado
* Escalable para futuras funcionalidades

---

# Resultado esperado

Generar una aplicación móvil lista para producción que incluya:

* Arquitectura completa del proyecto.
* Estructura de carpetas.
* Navegación.
* Pantallas.
* Componentes reutilizables.
* Servicios para consumir las APIs existentes.
* Manejo de autenticación.
* Manejo de estados.
* Consumo de formularios dinámicos.
* Subida de imágenes.
* Captura de firma.
* Sincronización offline.
* Manejo de errores.
* Indicadores de carga.
* Diseño moderno y profesional.
* Código limpio, mantenible y optimizado para producción.
