# Desactivación de pago en corresponsal de Wompi

El ecommerce usa el widget alojado de Wompi (`checkout.wompi.co/widget.js`).
El backend crea una intención `wompi` antes de abrirlo y recibe el método de
pago concreto solo después de que Wompi crea la transacción. La documentación
del widget no publica un parámetro para ocultar únicamente
`BANCOLOMBIA_COLLECT` (efectivo en corresponsal) y mantener tarjeta, PSE,
Nequi y Bancolombia. Rechazar el webhook después de un pago aprobado dejaría
al cliente cobrado sin pedido, por lo que **no** se hace eso.

**Acción del titular del comercio:** solicitar a soporte de Wompi la
inactivación temporal de **Efectivo en Corresponsales Bancolombia**
(`BANCOLOMBIA_COLLECT`) para la cuenta vinculada a la llave pública del sitio.
Confirmar en una compra de prueba del entorno sandbox que el widget ya no
muestre esa opción y que los demás medios permanezcan disponibles. Wompi
indica que la desactivación de un medio se solicita por sus canales de soporte:
https://soporte.wompi.co/hc/es-419/articles/10692449616787--C%C3%B3mo-puedo-tener-QR-bajo-el-modelo-agregador

El pago contra entrega propio del ecommerce, distinto al corresponsal dentro
de Wompi, queda deshabilitado en Django por defecto mediante
`CASH_ON_DELIVERY_ENABLED=False` y ya estaba oculto en React. Su futura
reactivación requiere habilitar ambos lados de forma coordinada.
