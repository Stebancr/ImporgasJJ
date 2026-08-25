# 🚀 Instalación Rápida - 3 Pasos

## ✅ Ya está configurado:
- ✅ Backend: `https://v8jsj64l-8000.use.devtunnels.ms`
- ✅ Iconos creados
- ✅ Archivo .env configurado
- ✅ app.json actualizado

---

## 📱 Generar APK para Instalar en tu Celular

### 🎯 MÉTODO RECOMENDADO: EAS Build (5 minutos)

#### 1️⃣ Instalar EAS CLI (solo primera vez)
```powershell
npm install -g eas-cli
```

#### 2️⃣ Login en Expo
```powershell
eas login
```
Si no tienes cuenta, créala gratis en: https://expo.dev/signup

#### 3️⃣ Generar el APK
```powershell
cd "c:\Users\luiss\Downloads\frontend\app intagas"
eas build --platform android --profile preview
```

**Espera 10-15 minutos**. El build se hace en la nube (no necesitas Android Studio).

#### 4️⃣ Descargar e Instalar
1. Cuando termine, te dará un **link de descarga**
2. Abre el link **en tu celular**
3. Descarga el APK
4. Instálalo (habilita "Fuentes desconocidas" si pregunta)

---

## 🎮 ALTERNATIVA: Probar con Expo Go (Sin instalar APK)

Si quieres probar **más rápido sin generar APK**:

#### 1️⃣ Instalar Expo Go en tu celular
Play Store: https://play.google.com/store/apps/details?id=host.exp.exponent

#### 2️⃣ Iniciar dev server
```powershell
cd "c:\Users\luiss\Downloads\frontend\app intagas"
npm install
npm start
```

#### 3️⃣ Escanear QR
- Abre Expo Go en tu celular
- Escanea el QR que aparece en la terminal
- ¡Listo! La app se carga automáticamente

**⚠️ Limitación**: Con Expo Go algunas funciones nativas pueden no funcionar perfectamente. Para pruebas completas, usa el APK.

---

## 📋 Comandos Rápidos

```powershell
# Navegar a la carpeta
cd "c:\Users\luiss\Downloads\frontend\app intagas"

# Instalar dependencias (primera vez)
npm install

# Ver configuración
cat app.json
cat .env

# Probar que el backend funciona
curl https://v8jsj64l-8000.use.devtunnels.ms/visits/

# Dev mode (Expo Go)
npm start

# Generar APK (EAS Build)
eas build --platform android --profile preview
```

---

## 🔍 Verificar que Todo Funciona

Antes de generar el APK, prueba con Expo Go:

1. `npm install` en la carpeta del proyecto
2. `npm start` para iniciar el servidor
3. Escanea el QR con Expo Go en tu celular
4. Prueba hacer login con un usuario técnico
5. Si funciona, genera el APK con EAS

---

## ❌ Si tienes problemas

### "Module not found"
```powershell
rm -r -force node_modules
npm install
```

### "Cannot connect to backend"
Verifica la URL:
```powershell
curl https://v8jsj64l-8000.use.devtunnels.ms/visits/
```

### EAS Build falla
Asegúrate de:
- Tener cuenta en expo.dev
- Haber hecho `eas login`
- `app.json` sea válido (JSON bien formado)

---

## 🎉 ¡Ya puedes instalar!

1. Ejecuta: `eas build --platform android --profile preview`
2. Espera 10-15 minutos
3. Descarga el APK en tu celular
4. Instala y prueba

**La app se llamará**: "Intagas Visitas"

---

## 📞 Contacto
servicioimporgas@gmail.com
