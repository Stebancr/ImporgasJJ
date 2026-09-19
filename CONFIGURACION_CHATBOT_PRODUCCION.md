# 🚀 CONFIGURACIÓN DEL CHATBOT IA EN PRODUCCIÓN

## ✅ Resumen

Los ajustes del chatbot (prompt, reglas, filtrado por categoría) **SÍ se mantienen automáticamente** cuando despliegas el contenedor en el servidor, porque están en el código Python (`ollama_service.py`).

**Lo único que necesitas configurar es descargar el modelo de IA.**

---

## 📋 Paso a Paso para Producción

### 1️⃣ **Configuración Automática (Recomendado)**

El archivo `docker-compose.dev.yml` ya está configurado para descargar el modelo automáticamente:

```bash
# En el servidor, levanta los servicios
docker compose -f docker-compose.dev.yml up -d

# El contenedor 'ollama' descargará automáticamente el modelo qwen:4b
# Esto puede tomar 5-10 minutos la primera vez
```

**Verificar que el modelo se descargó:**
```bash
docker exec ollama ollama list
# Debe mostrar: qwen:4b
```

---

### 2️⃣ **Configuración Manual (Si la automática falla)**

Si por alguna razón el modelo no se descarga automáticamente:

```bash
# Paso 1: Levantar solo el contenedor ollama
docker compose -f docker-compose.dev.yml up -d ollama

# Paso 2: Esperar 30 segundos
sleep 30

# Paso 3: Descargar el modelo manualmente
docker exec ollama ollama pull qwen:4b

# Paso 4: Levantar el resto de servicios
docker compose -f docker-compose.dev.yml up -d
```

---

## 🔧 Parámetros del Chatbot (Ya configurados)

Estos parámetros están en `BACKEND/crmChat/ollama_service.py` y **se aplican automáticamente**:

### ✅ Configuración Actual:

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| **Modelo** | `qwen:4b` | Modelo de IA ligero y rápido |
| **Temperatura** | `0.1` | Respuestas muy precisas y consistentes |
| **Max tokens** | `600` | Respuestas de longitud media |
| **Filtrado** | Inteligente por categoría | Detecta si piden calentador/regulador/aire y filtra productos |

### ✅ Reglas Implementadas:

1. ✅ **NO inventa productos** - Solo usa productos reales de la BD
2. ✅ **Filtra por categoría** - Si piden "calentador" solo muestra calentadores, NO reguladores
3. ✅ **NO muestra stock** - Nunca menciona cantidades disponibles
4. ✅ **Formato markdown** - Usa **negrilla** para nombres de productos
5. ✅ **Enlaces reales** - Todos los enlaces `/producto/{id}` son válidos
6. ✅ **Detección de intención** - Conecta con asesor cuando quieren comprar

---

## 🧪 Verificación Post-Deploy

Después de desplegar en producción, verifica que todo funcione:

```bash
# Test 1: Verificar que el modelo está cargado
docker exec ollama ollama list

# Test 2: Probar el chatbot (reemplaza TU_SERVIDOR con tu dominio/IP)
curl -X POST http://TU_SERVIDOR/api/crm-chat/bot/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"hola, muestrame calentadores"}'
```

**Respuesta esperada:**
- ✅ Solo muestra productos de categoría "Calentadores"
- ✅ NO muestra reguladores ni otros productos
- ✅ Usa formato markdown con **negrilla**
- ✅ Enlaces `/producto/{id}` válidos

---

## 📊 Recursos del Servidor

### Espacio en disco:
- **Modelo Ollama**: ~1 GB (descarga única)
- **Volumen ollama_data**: Crece hasta ~1.5 GB

### RAM recomendada:
- **Mínimo**: 2 GB para el contenedor ollama
- **Recomendado**: 4 GB para mejor rendimiento

---

## 🔄 Actualizar Parámetros del Bot

Si necesitas cambiar las reglas del chatbot en el futuro:

1. **Editar** `BACKEND/crmChat/ollama_service.py`
2. **Modificar** el `SYSTEM_PROMPT` o los parámetros de temperatura
3. **Reiniciar** el contenedor backend:
   ```bash
   docker restart backend
   ```

**NO necesitas reiniciar el contenedor ollama ni re-descargar el modelo.**

---

## 🐛 Troubleshooting

### Problema: "El bot sigue inventando productos"
**Solución:** 
```bash
docker restart backend
# Verifica que el código actualizado esté en el servidor
docker exec backend cat /app/crmChat/ollama_service.py | grep "REGLAS ABSOLUTAS"
```

### Problema: "Error connecting to Ollama"
**Solución:**
```bash
# Verificar que ollama esté corriendo
docker ps | grep ollama

# Ver logs de ollama
docker logs ollama

# Reiniciar ollama
docker restart ollama
```

### Problema: "Modelo no encontrado"
**Solución:**
```bash
# Descargar el modelo manualmente
docker exec ollama ollama pull qwen:4b

# Listar modelos disponibles
docker exec ollama ollama list
```

---

## 📁 Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| `BACKEND/crmChat/ollama_service.py` | Configuración del chatbot, prompt, reglas |
| `BACKEND/crmChat/views.py` | Endpoints de API del chat |
| `docker-compose.dev.yml` | Configuración de servicios (incluye ollama) |
| `frontend_U/src/components/Chatbot.tsx` | UI del chat de ecommerce |
| `frontend_S/src/app/pages/ChatPage.tsx` | UI del chat de asesores |

---

## ✨ Mejoras Futuras Opcionales

Si necesitas más precisión o capacidades:

1. **Modelo más grande**: Cambiar a `qwen2.5:3b` o `qwen2.5:7b`
   ```python
   # En BACKEND/core/settings.py
   OLLAMA_MODEL = 'qwen2.5:3b'  # Mejor pero usa más RAM
   ```

2. **GPU en servidor**: Para respuestas más rápidas
   ```yaml
   # En docker-compose
   ollama:
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
   ```

3. **Caché de respuestas**: Para preguntas frecuentes
   ```python
   # Implementar Redis cache en views.py
   ```

---

## 🎯 Resumen Final

**SÍ, los parámetros se mantienen automáticamente** porque están en tu código Python.

**Solo necesitas una configuración inicial**: Descargar el modelo (automático con el docker-compose actualizado).

**Proceso completo de deploy:**
```bash
# 1. Subir código al servidor
git pull origin main

# 2. Levantar servicios (descarga modelo automáticamente)
docker compose -f docker-compose.dev.yml up -d

# 3. Esperar ~5 minutos para descarga del modelo

# 4. Verificar
docker exec ollama ollama list
curl http://localhost/api/crm-chat/bot/chat/ -d '{"message":"hola"}'
```

¡Listo! 🚀
