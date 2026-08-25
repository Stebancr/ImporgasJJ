# 📱 Guía de Instalación - App Móvil Intagas Visitas

## 🎯 Configuración Completada

✅ **Backend configurado**: `https://v8jsj64l-8000.use.devtunnels.ms`  
✅ **Plataforma**: Android APK  
✅ **Archivo .env creado**  
✅ **app.json actualizado**  

---

## 📦 Opción 1: Build con EAS (Recomendado - Más Fácil)

EAS Build es el servicio oficial de Expo para crear APKs instalables.

### Paso 1: Instalar EAS CLI

```bash
npm install -g eas-cli
```

### Paso 2: Login en Expo

```bash
eas login
```

Si no tienes cuenta, créala en: https://expo.dev/signup

### Paso 3: Configurar proyecto

```bash
cd "c:\Users\luiss\Downloads\frontend\app intagas"
eas build:configure
```

### Paso 4: Crear los iconos (assets)

Crea estos archivos en la carpeta `assets/` (puedes usar cualquier imagen PNG):

- **icon.png** (1024x1024) - Icono principal
- **splash-icon.png** (512x512) - Splash screen
- **adaptive-icon.png** (1024x1024) - Icono adaptable Android
- **favicon.png** (48x48) - Favicon web

**💡 Tip rápido**: Puedes usar este generador online:
https://www.appicon.co/ (sube una imagen y genera todos los tamaños)

O descarga iconos temporales aquí:
https://www.flaticon.com/free-icon/gas_3063822

### Paso 5: Generar APK

```bash
# Para un APK de prueba (interno)
eas build --platform android --profile preview

# Para un APK de producción
eas build --platform android --profile production
```

El build se hace **en la nube** (no necesitas Android Studio instalado).

⏱️ **Tiempo estimado**: 10-15 minutos

### Paso 6: Descargar e Instalar

1. Cuando termine, te dará un link de descarga
2. Abre el link en tu celular
3. Descarga el APK
4. Instala (habilita "Instalar de fuentes desconocidas" en Ajustes → Seguridad)

---

## 📦 Opción 2: Build Local con Expo (Sin Cuenta)

Si no quieres crear cuenta en Expo, puedes hacer un build local.

### Requisitos:
- Java JDK 17
- Android SDK
- Android Studio (o solo las herramientas CLI)

### Pasos:

```bash
cd "c:\Users\luiss\Downloads\frontend\app intagas"

# Instalar dependencias
npm install

# Crear assets (ver paso 4 arriba)

# Pre-build (genera carpeta android/)
npx expo prebuild --platform android

# Build APK
cd android
./gradlew assembleRelease

# El APK estará en:
# android/app/build/outputs/apk/release/app-release.apk
```

Este método requiere más configuración pero no depende de servicios externos.

---

## 🚀 Opción 3: Desarrollo con Expo Go (Más Rápido para Pruebas)

Para probar sin instalar APK, usa Expo Go:

### Paso 1: Instalar Expo Go en tu celular

Descarga desde Play Store: https://play.google.com/store/apps/details?id=host.exp.exponent

### Paso 2: Iniciar servidor de desarrollo

```bash
cd "c:\Users\luiss\Downloads\frontend\app intagas"
npm install
npm start
```

### Paso 3: Escanear QR

- Abre Expo Go en tu celular
- Escanea el código QR que aparece en la terminal
- La app se cargará automáticamente

**⚠️ Limitación**: Con Expo Go no puedes usar todas las funcionalidades nativas (cámara, secure-store). Para probar todo, necesitas el APK.

---

## 🎨 Crear Iconos Rápido (Sin Diseño)

Si no tienes iconos, puedes crear unos simples con fondo azul IMPORGAS:

### Usando PowerShell + ImageMagick:

```powershell
# Instalar ImageMagick
winget install ImageMagick.ImageMagick

cd "c:\Users\luiss\Downloads\frontend\app intagas\assets"

# Crear iconos con texto
magick -size 1024x1024 xc:"#1e3a5f" -gravity center -pointsize 300 -fill white -annotate +0+0 "I" icon.png
magick -size 512x512 xc:"#1e3a5f" -gravity center -pointsize 150 -fill white -annotate +0+0 "I" splash-icon.png
magick -size 1024x1024 xc:"#1e3a5f" -gravity center -pointsize 300 -fill white -annotate +0+0 "I" adaptive-icon.png
magick -size 48x48 xc:"#1e3a5f" -gravity center -pointsize 24 -fill white -annotate +0+0 "I" favicon.png
```

O copia cualquier imagen PNG y renómbrala (Expo redimensionará automáticamente).

---

## ✅ Verificar Configuración

Antes de hacer el build, verifica:

```bash
cd "c:\Users\luiss\Downloads\frontend\app intagas"

# Ver configuración
cat app.json

# Probar que conecta con backend
npm start
# Escanear QR con Expo Go y probar login
```

---

## 🔧 Solución de Problemas

### Error: "Module not found"
```bash
rm -rf node_modules
npm install
```

### Error: "No se puede conectar al backend"
Verifica que la URL en `.env` sea correcta y esté accesible:
```bash
curl https://v8jsj64l-8000.use.devtunnels.ms/visits/
```

### Error de permisos en Android
Asegúrate de que `app.json` tenga:
```json
"permissions": [
  "CAMERA",
  "READ_EXTERNAL_STORAGE",
  "WRITE_EXTERNAL_STORAGE"
]
```

---

## 📝 Checklist Final

- [ ] Carpeta `assets/` creada con los 4 iconos
- [ ] Archivo `.env` con URL correcta del backend
- [ ] `npm install` ejecutado sin errores
- [ ] Backend accesible desde el celular
- [ ] Cuenta en expo.dev creada (para EAS build)
- [ ] EAS CLI instalado (`eas --version`)
- [ ] Build iniciado con `eas build --platform android --profile preview`

---

## 🎉 ¡Listo!

Una vez tengas el APK:

1. **Descárgalo** en tu celular
2. **Instálalo** (habilita fuentes desconocidas si pregunta)
3. **Abre la app** "Intagas Visitas"
4. **Login** con tus credenciales de técnico
5. **Prueba el flujo completo**: Ver visitas → Iniciar → Completar formulario → Fotos → Firma

---

## 📞 Soporte

Si tienes problemas:

1. Verifica logs: `npm start` y mira errores en consola
2. Prueba primero con Expo Go antes de hacer build
3. Revisa que el backend esté activo: `curl https://v8jsj64l-8000.use.devtunnels.ms/visits/`

**Contacto**: servicioimporgas@gmail.com

---

**Recomendación**: Usa **Opción 1 (EAS Build)** - es la más fácil y rápida ✅
