# Rollback que no reabre sesiones

El main anterior 9d1edf49 no comprueba la versión global. Volver a sus autenticadores después del corte contradice el requisito de no reactivar credenciales revocadas. Conservar sus imágenes y respaldos sirve para recuperación de componentes/datos, pero **no autoriza reiniciar su autenticación**.

Para el primer corte de seguridad se prepara una imagen mínima de mantenimiento que responde 503 a toda operación y no autentica ninguna credencial. Escucha los puertos esperados por backend, frontend y gateway; /health indica explícitamente mantenimiento y autenticación desactivada. No es una plataforma funcional ni debe reportarse como despliegue exitoso. Preserva PostgreSQL, Redis, media, las claves nuevas y la versión global. Después de verificar una versión de aplicación con el guard global en producción, esa versión puede ser el rollback compatible de una promoción funcional posterior.

Preparación antes del corte, con etiqueta registrada y sin secretos en el contexto:

```sh
docker build -t imporgas-security-maintenance:ETIQUETA_VERIFICADA qa/security/maintenance
```

Ante error crítico: detener la promoción y los workers/Beat; cerrar transportes de aplicación; mantener servicios de datos. Conservar logs sanitizados y verificar las colas/entregas inciertas para no reenviar mensajes. Utilizar el override qa/security/maintenance/compose.rollback.yml con SECURITY_MAINTENANCE_TAG definida a la imagen previamente verificada. Recrear únicamente backend/frontend/gateway con --no-build --no-deps, recargar Nginx después de validar sintaxis y comprobar que login/API/handshakes reciben 503. No ejecutar esta operación solo por un healthcheck transitorio sin diagnosticar.

No restaurar base, no revertir usuarios.0010, no disminuir epoch, no recuperar la clave JWT anterior, no arrancar autenticación legacy y no borrar volúmenes. La corrección se hace en Git/PR y se promueve hacia adelante. La indisponibilidad temporal es preferible a reabrir una credencial comprometida. No se ha aplicado este override en producción.
