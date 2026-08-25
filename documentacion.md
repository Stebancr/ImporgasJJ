Usa nuestra API de Pagos a Terceros
1. Funcionamiento del API
Nuestra API de pagos resuelve este problema al ofrecer una herramienta robusta, optimizada para procesar pagos en tiempo real y adaptada a múltiples escenarios de negocio, buscando que nuestros clientes puedan realizar su dispersión de pagos desde plataformas o aplicaciones propias.

El API de Pagos a Terceros de Wompi facilita la dispersión de pagos a cuentas bancarias en Colombia mediante la creación y gestión de lotes de pagos. Los usuarios pueden enviar pagos de manera individual o en lotes, utilizando archivos compatibles o mediante solicitudes JSON.

Contamos con un ambiente Sandbox para que los clientes puedan simular pagos, consultar respuestas, simular recargas de saldo de cuentas origen y validar reportes de pagos en ambiente de prueba.
El API permite utilizar múltiples cuentas origen: Wompi cuenta, cuentas Bancolombia y cuentas de otros bancos autorizados.
Se ha incorporado soporte de idempotencia para evitar la duplicidad de pagos.
Notificación de eventos mediante un webhook.
Adicionalmente, ofrecemos un Dashboard donde los clientes pueden:
Consultar trazabilidad de transacciones en producción.
Visualizar el debugger de los eventos API.
Descargar reportes de pagos procesados.
2. Tipos de pagos disponibles a través del API
Nuestra API de dispersión de pagos ofrece flexibilidad para adaptarse a diferentes necesidades de negocio. A través de la integración, puedes realizar los siguientes tipos de pagos:

Pagos inmediatos: Permite ejecutar una orden de pago en el momento en que se solicita. Ideal para operaciones que requieren procesamiento en tiempo real, como pagos a proveedores o desembolsos a usuarios finales.

info
Tener en cuenta los ciclos de procesamiento ACH y cuenta origen de la dispersión

Pagos programados: Permite agendar pagos para que se procesen en una fecha específica futura. Esta funcionalidad es útil para planificar pagos de nómina, obligaciones recurrentes o pagos a terceros en fechas pactadas.

Pagos recurrentes: Permite configurar pagos que se ejecuten de manera periódica (por ejemplo, semanal, quincenal o mensual). Esta opción es ideal para automatizar pagos recurrentes como membresías o servicios periódicos.

Cada tipo de pago puede ser gestionado de manera sencilla a través de los endpoints de creación de órdenes de pago, definiendo los parámetros necesarios como el tipo de programación, la fecha deseada de ejecución y el detalle de los destinatarios.

Nota
Importante: Los pagos programados y recurrentes quedarán registrados en el sistema y serán ejecutados de acuerdo con la configuración establecida al momento de la creación. Consulta más adelante cómo realizar la configuración de cada tipo de pago.

3. Flujo general para la integración
3.1. Autenticación
Obtener las llaves de autenticación (API Key y ID Usuario Principal) desde el dashboard de Wompi.

Ver Llaves de autenticación

3.2. Creación de Lote
Pago uno a uno: Enviar una solicitud POST al endpoint /payouts con el detalle de las transacciones en formato JSON. Ver Crea tu primer lote
Pago mediante archivo: Enviar una solicitud POST al endpoint /payouts/file adjuntando un archivo en uno de los formatos soportados (WOMPI, SAP, PAB, DISFON, BANCO_OCCIDENTE_FC, DAVIVIENDA). Ver Crea un lote de pago por archivo
3.3 Validación de los datos enviados:
Wompi valida los datos proporcionados y los envía a procesar.

3.4 Procesamiento de los lotes de pago e inicio del proceso de pago
Wompi procesa las transacciones enviadas en los lotes y realiza el proceso de pago, utilizando el mismo banco o ACH según la cuenta seleccionada.

3.5. Consultas y eventos del cambio de estado de las transacciones
Consultar el estado de los lotes y transacciones utilizando los endpoints proporcionados para obtener información detallada o la actualización de cada pago enviadas a través del webhook.

Ver más sobre Consultas

Ver más sobre Eventos

3.6. Reportes:
Reportes consolidados por lotes y transacciones disponibles a través del API o el dashboard de Wompi.

Ver más sobre Reportes

4. Consideraciones generales
Moneda: Todas las transacciones se realizan en pesos colombianos (COP).
Montos: Los montos se manejan en centavos y en formato entero, donde los dos ultimos digitos corresponden a los centavos Ej. 100000 equivalente a $1000,00
Llaves de Autenticación: Es esencial obtener las llaves de autenticación (API Key y ID Usuario Principal) desde el dashboard de Wompi para interactuar con el API. Ver Llaves de autenticación
Formatos de archivo soportados: Al crear lotes mediante archivos, el API está en la capacidad de soportar y traducir los siguientes formatos: Plantilla Wompi, PAB y SAP Bancolombia, DISFON Banco de Bogotá, Banco de Occidente FC, Davivienda.
Límites y restricciones: Existe un límite transaccional diario de $1.500.000.000 este límite se puede ampliar o disminuir si el cliente lo requiere. Existen restricciones en cuanto al número de lotes diarios que se pueden enviar por cliente el cual es de 3.800 lotes diarios, sin embargo, cada lote no tiene restricciones en cuanto al número de transacciones que puede contener. En caso de necesitar ajustar los límites, contáctate con soporte.
Idempotencia: Implementada para evitar pagos duplicados usando una llave unica generada por el cliente y que expira en 24 horas.
Sandbox: Entorno disponible para simular escenarios de prueba equivalente al entorno productivo.
Horarios de procesamiento: Los pagos se procesan en los horarios establecidos por Wompi y las entidades bancarias. Es recomendable consultar estos horarios para garantizar el procesamiento oportuno de las transacciones.
Horarios procesamiento

5. Datos requeridos para un pago
Al crear un lote de pagos, se deben proporcionar los siguientes datos para cada transacción:

legalIdType (String): Tipo de identificación del beneficiario (CC, NIT, CE).
legalId (String): Número de identificación del beneficiario.
bankId (UUID): Identificador único del banco, obtenido del endpoint /banks.
accountType (String): Tipo de cuenta bancaria (AHORROS, CORRIENTE).
accountNumber (String): Número de la cuenta bancaria. Debe contener solo números y ser diferente de cero.
name (String): Nombre completo del beneficiario.
email (String): Correo electrónico del beneficiario.
amount (Integer): Monto a transferir en centavos (por ejemplo, $10,000 COP se representa como 1000000).
reference (String): Referencia única para la transacción.
accountId (String): Identificador de la cuenta de origen, obtenido del endpoint /accounts.
paymentType (String): Tipo de pago (PAYROLL, PROVIDERS, OTHER).
6. Tipos de cuenta bancaria
Los tipos de cuenta bancaria admitidos por el API son:

AHORROS: Cuenta de ahorros.
CORRIENTE: Cuenta corriente.
7. Códigos de Bancos en Colombia
Para obtener la lista actualizada de bancos y sus identificadores únicos (bankId), se debe consultar el endpoint /banks proporcionado por Wompi.

Banco	Código
BANCO DE BOGOTA	1001
BANCO POPULAR	1002
ITAU antes Corpbanca	1006
BANCOLOMBIA	1007
CITIBANK	1009
BANCO GNB SUDAMERIS	1012
BBVA COLOMBIA	1013
ITAU	1014
SCOTIABANK COLPATRIA S.A	1019
BANCO DE OCCIDENTE	1023
BANCOLDEX S.A.	1031
BANCO CAJA SOCIAL BCSC SA	1032
BANCO AGRARIO	1040
BANCO MUNDO MUJER	1047
BANCO DAVIVIENDA SA	1051
BANCO AV VILLAS	1052
BANCO W S.A	1053
BANCAMIA S.A	1059
BANCO PICHINCHA	1060
BANCOOMEVA	1061
BANCO FALABELLA S.A.	1062
BANCO FINANDINA S.A.	1063
BANCO SANTANDER DE NEGOCIOS CO	1065
BANCO COOPERATIVO COOPCENTRAL	1066
MIBANCO S.A.	1067
BANCO SERFINANZA S.A	1069
LULO BANK S.A.	1070
BANCO J.P. MORGAN COLOMBIA S.A	1071
FINANCIERA JURISCOOP S.A. COMP	1121
COOPERATIVA FINANCIERA DE ANTI	1283
JFK COOPERATIVA FINANCIERA	1286
COOTRAFA COOPERATIVA FINANCIER	1289
CONFIAR COOPERATIVA FINANCIERA	1292
BANCO UNION S.A	1303
COLTEFINANCIERA S.A	1370
NEQUI	1507
DAVIPLATA	1551
BANCO CREDIFINANCIERA SA.	1558
PIBANK	1560
IRIS	1637
MOVII	1801
DING TECNIPAGOS SA	1802
POWWI	1803
Ualá	1804
BANCO BTG PACTUAL	1805
BOLD CF	1808
NU	1809
RAPPIPAY	1811
COINK	1812
GLOBAL66	1814
BANCO CONTACTAR S.A.	1819
8. Validaciones Bancarias
El número de cuenta debe ser numérico y tener entre 6 y 20 caracteres.

El código del banco debe ser válido y estar en la lista de bancos admitidos.
Los pagos a cuentas bloqueadas o inactivas serán rechazados.
El beneficiario debe coincidir con el titular de la cuenta en algunos bancos.
Validaciones de saldo y límites diarios antes de procesar el pago.
9. Estados de Lotes y Transacciones
Estados de un lote
Estado lotes		¿Es un estado final?	Descripción
PENDING_APPROVAL	Por aprobar	No	Estado inicial del lote, que será revisado y aprobado / rechazado por parte del rol aprobador. Aplica a pagos creados solo desde el dashboard de Wompi.
PENDING	En proceso	No	Lote de pago aprobado por el rol aprobador, que está en proceso de ejecución.
NOT_APPROVED	No aprobado	No	Lote de pago que ha sido rechazado por el rol aprobador.
REJECTED	Rechazado	Sí	Lote de pago rechazado por incumplimiento de políticas, errores bancarios, errores del archivo o restricciones de cuenta.
PARTIAL_PAYMENT	Pago parcial	No	Se da cuando un lote de pagos contiene transacciones en diferentes estados, algunas ya finalizadas y otras aun en proceso.
TOTAL_PAYMENT	Procesado	Sí	Todas las transacciones del lote han sido gestionadas y cuentan con un estado final, ya sea aprobado o rechazado.
Estados de Transacción:
Estado transacciones		¿Es un estado final?	Descripción
PENDING	En proceso	No	La transacción está en trámite o pendiente de ser aplicada en la cuenta del beneficiario.
APPROVED	Pagado	Si	La transacción se aplicó exitosamente en la cuenta del beneficiario.
CANCELLED	Cancelado	Si	La transacción no fue procesada y debe ser cargada nuevamente. Se genera cuando el aprobador rechaza el pago.
FAILED	Rechazado	Si	La transacción no se acreditó al beneficiario debido a información incorrecta o restricciones en la cuenta destino.
10. Causales de rechazo más comunes
Codigo	Descripción	Estado
D02	Banco no existe	FAILED
D04	Tipo transacción invalido	FAILED
D06	Oficina pago no numérica	FAILED
D07	Numero cuenta no existe	FAILED
D09	Código referencia no numérico	FAILED
D10	Cuenta no autorizada para acreditar	FAILED
D11	Cuenta Nit no corresponden	FAILED
D12	Nit proveedor no inscrito para pagos	FAILED
D14	Valor errado en transacción no monetaria	FAILED
D15	Pago cheque o efectivo no permitido	FAILED
D18	Nit no numérico	FAILED
D19	Fondos insuficientes	FAILED
D21	Falta nombre beneficiario	FAILED
D24	Valor 0 en destino	FAILED
D25	Nit en ceros	FAILED
D29	Nit pagador no inscrito servicio tarjetas	FAILED
D30	Transacción no válida para clase de pago	FAILED
D31	Estado cuenta pensión cancelada	FAILED
D32	Código de banco no numérico	FAILED
D33	Código banco en ceros	FAILED
D34	Número de cuenta no numérico	FAILED
D35	Fecha de aplicación invalida	FAILED
D37	Oficina no valida	FAILED
D39	Tipo identificación invalido	FAILED
D40	Oficina no autorizada para transacción	FAILED
D41	Pago sin cedula de autorizado	FAILED
D44	Pensionado no inscrito para la entidad	FAILED
D45	Cuenta pensión no inscrita para entidad pagadora	FAILED
D49	Código de banco no permitido	FAILED


Crea tu primer lote
Puedes crear lotes de pago de dos maneras, enviando el detalle de las transacciones como un JSON en el cuerpo de la solicitud, o enviando uno de los formatos de archivos que soportamos.

URL Base del API
https://api.payouts.wompi.co/v1

https://api.payouts.wompi.co/v2

Crear un lote de pago
La URL del endpoint para crear lotes de pagos manual es:

POST /payouts

Cabeceras (Headers)
x-api-key: *******
user-principal-id: *******
idempotency-key: Rs122k1sas
Content-Type: application/json

Los headers user-principal-id y x-api-key son para la autenticación. Mas detalles de como obtenerlos en Llaves de autenticación
El header idempotency-key se usa para garantizar que el pago sea único y evitar duplicidad. Debe ser una llave que tenga de 1 a 64 caracteres, puede contener letras y números, el único caracter especial permitido dentro de la llave es el guion (-). Debe ser unico y expira en 24 horas.
El header Content-Type debe ir con el valor application/json especificando que el formato del cuerpo de la petición.
Pagos inmediatos
A continuación se muestra un ejemplo del cuerpo de una petición:

{
  "reference": "payment-reference",
  "accountId": "account-id",
  "paymentType": "PAYROLL",
  "transactions": [
    {
      "legalIdType": "CC",
      "legalId": "1000000000",
      "bankId": "00000000-0000-0000-0000-000000000000",
      "accountType": "AHORROS",
      "accountNumber": "00000000",
      "name": "John Doe",
      "email": "email@example.com",
      "amount": 1000000,
      "reference": "custom-transaction-reference"
    }
  ]
}

El campo accountId se debe extraer de la respuesta del endpoint /accounts. Ir a consultar cuentas.
El campo bankId se debe extraer de la respuesta del endpoint /banks. Ir a consultar bancos.
El valor de amount debe ser un valor positivo y debe ir en centavos. (por ejemplo, $10,000 COP se representa como 1000000).
Pagos programados
Para crear pagos programados, puedes agregar el campo dispersionDatetime el cual es un string con el formato YYYY-MM-DDTHH:mm.

info
La fecha de programación del pago debe ser minimo al siguiente día en que se genere la petición, de lo contrario el pago es rechazado.

Ejemplo del cuerpo de la petición:

{
  "reference": "referencia-api",
  "accountId": "account-id",
  "paymentType": "PAYROLL",
  "dispersionDatetime": "2024-10-15T19:01",
  "transactions": [
    {
      "legalIdType": "CC",
      "legalId": "1000000000",
      "bankId": "00000000-0000-0000-0000-000000000000",
      "accountType": "AHORROS",
      "accountNumber": "00000000",
      "name": "John Doe",
      "email": "email@example.com",
      "amount": 1000,
      "reference": "custom-transaction-reference"
    }
  ]
}

Pagos recurrentes
Para crear pagos recurrentes debes agregar los campos dispersionDatetime el cual es un string con el formato YYYY-MM-DDTHH:mm y recurring el cual es un objeto json que recibe los siguientes campos:

interval: Intervalo del pago. Puede ser: biweek, month.
months: Meses en número. Puede ser: 3, 6, 12.
description: La descripción es opcional.
{
  "reference": "referencia-api",
  "accountId": "account-id",
  "paymentType": "PAYROLL",
  "dispersionDatetime": "2024-10-15T19:01",
  "recurring": {
    "interval": "biweek",
    "months": 3,
    "description": "optional description"
  },
  "transactions": [
    {
      "legalIdType": "CC",
      "legalId": "1000000000",
      "bankId": "00000000-0000-0000-0000-000000000000",
      "accountType": "AHORROS",
      "accountNumber": "00000000",
      "name": "John Doe",
      "email": "email@example.com",
      "amount": 1000,
      "reference": "custom-transaction-reference"
    }
  ]
}

Crear un lote de pago enviando un archivo
La URL del endpoint para crear lotes de pagos por archivo es:

POST /payouts/file

Formatos
Puedes crear un lote de pago usando uno de los siguientes archivos que soportamos:

Formato	Código	Extensión	Plantilla	Ejemplo
Wompi	WOMPI	.csv	Plantilla	Descargar
PAB Bancolombia	PAB	.txt	Conversor	Descargar
SAP Bancolombia	SAP	.txt	Conversor	Descargar
Disfon - Banco de Bogotá	DISFON	.txt		Descargar
FlexCube (FC) - Banco de Occidente	BANCO_OCCIDENTE_FC	.txt		Descargar
Plano Davivienda	DAVIVIENDA	.txt		Descargar
Cabeceras (Headers)
x-api-key: *******
user-principal-id: *******
idempotency-key: Rs122k1sas
Content-Type: multipart/form-data

Los headers user-principal-id y x-api-key son para la autenticación. Mas detalles de como obtenerlos en Llaves de autenticación
El header idempotency-key se usa para garantizar que el pago sea único y evitar duplicidad. Debe ser una llave que tenga de 1 a 64 caracteres, puede contener letras y números, el único caracter especial permitido dentro de la llave es el guion (-). Debe ser unico y expira en 24 horas.
El header Content-Type para los pagos por archivo debe ir con el valor multipart/form-data
Pagos inmediatos
El cuerpo de la petición debe ser del tipo form-data con los campos:

reference: Referencia del lote.
file: Archivo del lote.
fileType: Tipo de archivo. Es el código del formato, ver tabla de formatos. Ej. BANCO_OCCIDENTE_FC
accountId: Id de la cuenta origen
paymentType: Tipo de pago. Puede ser: PAYROLL, PROVIDERS, OTHER.
Archivos comprimidos
Para subir un archivo de lote comprimido, este debe tener la extensión .gz y el MIME application/gzip. También se deben adicionar los siguientes campos a la petición:

fileName: Nombre del archivo y con la extensión original (antes de comprimirse). Por ejemplo, "plantilla-wompi.csv".
fileMime: MIME del archivo original (antes de comprimirse). Por ejemplo, "text/csv".
Pagos programados
Para crear pagos programados se debe adicional el siguiente campo:

dispersionDatetime: Campo que representa la hora y fecha de dispersión con el formato YYYY-MM-DDTHH:mm
info
La fecha de programación del pago debe ser minimo al siguiente día en que se genere la petición, de lo contrario el pago es rechazado.

Pagos recurrentes
Para crear pagos recurrentes debes agregar los siguientes campos:

dispersionDatetime: Campo que representa la hora y fecha de dispersión con el formato YYYY-MM-DDTHH:mm
interval: Intervalo del pago. Puede ser: biweek, month.
months: Meses en número. Puede ser: 3, 6, 12.
description: La descripción es opcional.

Ambiente sandbox
El ambiente sandbox de la API de Pagos a Terceros es un entorno de pruebas diseñado para que desarrolladores e integradores puedan simular transacciones y validar sus integraciones de forma segura, sin procesar pagos reales. Este entorno replica el comportamiento del ambiente de producción, permitiendo probar flujos de pago, validaciones de seguridad, respuestas del API y manejo de errores sin afectar a usuarios finales ni generar cargos reales.

En esta documentación encontrarás todo lo necesario para comenzar a trabajar con el sandbox: cómo obtener credenciales de prueba, ejemplos de peticiones, escenarios simulables y buenas prácticas para asegurar una integración exitosa antes del paso a producción.

Importante
Aunque los datos y comportamientos en sandbox imitan el entorno de producción, pueden existir ligeras diferencias. Asegúrate de realizar pruebas completas antes de lanzar tu integración al público.

Llaves de sandbox
Las llaves de sandbox se obtienen de la misma manera que las llaves productivas, con la particularidad de que el ingresar a la página de programadores se debe cambiar al modo normal, como se muestra a continuación:

Ver llaves sandbox

Desde el modo sandbox también se permite:

Ver llaves
Regenerar llaves
Configurar URL de eventos
Ver secreto para la integración de eventos
URL Base de Sandbox
Todos los endpoints productivo estan disponible en el ambiente sandbox

https://api.sandbox.payouts.wompi.co/v1

Recuerda usar las cabeceras (headers) de todas las solicitudes que se realicen tambien en la API de sandbox. Ejemplo:

user-principal-id: {ID_Usuario_Principal}
x-api-key: {API_Key}

Simular estado de transacciones
En sandbox la solicitud de creación de pago manual (en formato JSON) o por archivo son iguales, la única diferencia es que desde sandbox se permite definir el estado final de las transacciones, para que estas queden aprobadas (APPROVED) o fallidas (FAILED)

Nota
Este campo es opcional; si no se envía, por defecto las transacciones quedan aprobadas (APPROVED)

Pago manual
Para simular el estado final de las transacciones, se debe enviar la propiedad transactionStatus (ver línea 5) con el valor APPROVED o FAILED.

{
  "reference": "payment-reference",
  "accountId": "account-id",
  "paymentType": "PAYROLL",
  "transactionStatus": "FAILED",
  "transactions": [
    {
      "legalIdType": "CC",
      "legalId": "1000000000",
      "bankId": "00000000-0000-0000-0000-000000000000",
      "accountType": "AHORROS",
      "accountNumber": "00000000",
      "name": "John Doe",
      "email": "email@example.com",
      "amount": 1000000,
      "reference": "custom-transaction-reference"
    }
  ]
}

Pago por archivo
Se debe agregar la propiedad transactionStatus al form-data.

Recargar saldo de una cuenta
El entorno sandbox de Wompi incluye un endpoint exclusivo para recargar saldo en cuentas de prueba, permitiendo simular operaciones que requieren fondos disponibles.

Importante
Esta funcionalidad solo está disponible en sandbox y no afecta cuentas reales.

La URL del endpoint para recargar cuenta es:

POST /accounts/balance-recharge

Se debe enviar en el body de la petición los campos de accountId (id de la cuenta a recargar) y amount (cantidad a recargar en centavos). Debe ser minimo $1000,00 y maximo $50.000.000,00

Nota
El accoutId se obtiene al consultar las cuentas. VerConsultar cuentas y saldos

{
  "accountId": "account-id",
  "amountInCents": 340000000
}


Consultas y operaciones
Consulta cuentas, saldos, lotes, transacciones y mas de manera sencilla, obteniendo información detallada a través de nuestras herramientas disponibles.

URLs base del API
Productivo:

https://api.payouts.wompi.co/v1

Sandbox: Todos los endpoints estan disponibles en ambiente sandbox

https://api.sandbox.payouts.wompi.co/v1

Consultar bancos
La URL del endpoint para consultar los bancos es:

GET /banks

Consultar cuentas y saldo
La URL del endpoint para consultar los saldos de las cuentas disponibles es:

GET /accounts

En la respuesta de la consulta, dentro de los detalles de cada cuenta, el campo balanceInCents hace alusión al saldo disponible en la cuenta, expresado en centavos. Los últimos dos dígitos son los centavos.

Se pueden filtrar los registros enviando query params (parámetros de la url) opcionales en la petición:

bankCodes: Códigos de los bancos, uno o más códigos separados por comas. por ejemplo: BANCOLOMBIA, BANCO_BOGOTA.
status: Estado de la cuenta. Se debe enviar alguno de los siguientes valores IN_REVIEW, ACTIVE, INACTIVE.
Sandbox
En el ambiente sandbox, no se usan cuentas bancarias reales. El sistema genera automáticamente cuentas de prueba para simular los pagos.

Consultar límites
La URL del endpoint para consultar los límites es:

GET /limits

En la respuesta de la consulta, dentro de los detalles de cada cuenta, el campo dailyLimit hace alusión al límite diario, expresado en centavos. Los últimos dos dígitos son los centavos.

Consultar lotes
La URL del endpoint para consultar todos los lotes es:

GET /payouts

Se pueden filtrar los registros enviando query params (parámetros de la url) opcionales en la petición:

status: Estado del lote, uno o más estados separados por comas. por ejemplo: PENDING, REJECTED. Los posibles valores son: PENDING, REJECTED, TOTAL_PAYMENT, PARTIAL_PAYMENT, PENDING_APPROVAL, NOT_APPROVED.
fromDate: "Fecha desde" la que se desea filtra, con el formato YYYY-MM-DD. Por ejemplo, 2024-01-01.
toDate: "Fecha hasta" la que se desea filtra, con el formato YYYY-MM-DD. Por ejemplo, 2024-02-01.
reference: Referencia del lote.
id: Id del lote.
limit: Valor numérico opcional para limitar el número de registros a mostrar.
page: Valor numérico opcional para paginar los registros.
Consultar un lote específico
La URL del endpoint para consultar un lote específico es:

GET /payouts/{payoutId}

Consultar transacciones de un lote
La URL del endpoint para consultar las transacciones de un lote es:

GET /payouts/{payoutId}/transactions

Se pueden filtrar los registros enviando query params (parámetros de la url) opcionales en la petición:

status: Estado de las transacciones. Se debe enviar alguno de los siguientes valores PROCESSING, PENDING, APPROVED, FAILED, REJECTED.
reference: Referencia de la transacción.
accountNumber: Número de cuenta.
payeeName: Nombre del beneficiario.
limit: Valor numérico opcional para limitar el número de registros a mostrar.
page: Valor numérico opcional para paginar los registros.
Consultar una transacción específica de un lote
La URL del endpoint para consultar una transacción específica de un lote es:

GET /payouts/{payoutId}/transactions/{transactionId}

Consultar transacciones de un lote por referencia
La URL del endpoint para consultar las transacciones de un lote por referencia es:

GET /transactions/{reference}

Se pueden filtrar los registros enviando query params (parámetros de la url) opcionales en la petición:

status: Estado de la transacciones. Se debe enviar alguno de los siguientes valores PENDING, APPROVED, CANCELLED, FAILED.
limit: Valor numérico opcional para limitar el número de registros a mostrar.
page: Valor numérico opcional para paginar los registros.
Consultar reportes
La URL del endpoint para consultar los reportes es:

GET /reports/payouts

Los query params (parámetros de la url) que se deben enviar en la petición deben ser:

periodicity: Periodicidad del informe. Puede ser: daily, weekly, biweekly, monthly.
reportType: Tipo de reporte. Puede ser: payouts, transactions.
limit: Valor numérico opcional para limitar el número de registros a mostrar.
page: Valor numérico opcional para paginar los registros.
Descargar reporte
La URL del endpoint para obtener el CSV de un reporte es:

GET /reports/presigned_url

Los query params (parámetros de la url) que se deben enviar en la petición deben ser:

reportExecutionId: _id del reporte.
reportIntegration: Tipo de reporte. Puede ser payouts, merchant_reports.
Monitoreo de Disponibilidad
La URL del endpoint para consultar la disponibilidad de los servicios internos es:

GET /health

Este endpoint permite verificar el estado de salud de los servicios que componen Pagos a Terceros, tales como users, payments, notifications y afe-rules-engine.

Los servicios se clasifican en dos categorías:

Críticos: users y payments
Secundarios: notifications y afe-rules-engine
En la respuesta se indica:

status: Un estado general de Pagos a Terceros. Puede tomar uno de los siguientes valores:
HEALTHY: Todos los servicios están operativos.
PARTIAL_OUTAGE: Todos los servicios críticos están operativos, pero al menos un servicio secundario presenta interrupciones.
UNHEALTHY: Al menos un servicio crítico no está operativo.
services: Lista de los servicios monitoreados. Cada uno incluye:
name: Nombre del servicio.
healthy: Indica si el servicio está disponible (true) o no (false).


Eventos
Cuando realizas pagos a través de la API de Pagos a terceros, es importante que tu sistema pueda mantenerse actualizado sobre el estado de cada operación. Para esto, Wompi ofrece un mecanismo de eventos vía webhook, que permite recibir notificaciones automáticas cada vez que ocurre un cambio relevante en el ciclo de vida de un pago.

Estos eventos son enviados a la URL que configures previamente y contienen información detallada sobre la operación, como su estado actual, valores, timestamps y referencias asociadas, entre otros. Esta funcionalidad es clave para mantener la trazabilidad de los pagos y automatizar flujos de negocio basados en su resultado.

tip
Ideal para mantener tu sistema sincronizado con el estado real de las transacciones.

Como configurar la URL de eventos
Puedes registrar una URL para recibir eventos tanto en el ambiente sandbox como en el de producción, desde el dashboard de Wompi.

Inicia sesión en tu cuenta principal en nuestro dashboard de comercios.
Busca y selecciona la opción Desarrollo en el menú principal.
Dentro de Desarrollo, elige la opción Programadores.
En la parte superior izquierda, selecciona Pagos a Terceros.
Ingresa la URL pública donde recibirás los eventos y guarda los cambios.
Sandbox
Puedes cambiar al modo sandbox y configurar la URL de eventos para este entorno

Configurar url de eventos

Generalidades de los eventos
Para que tu endpoint reciba correctamente los eventos, debe cumplir con los siguientes requisitos:

Método HTTP: Debe aceptar peticiones POST.
Protocolo: Debe usar HTTPS (no se permiten URLs sin cifrado).
Accesibilidad: Debe ser públicamente accesible desde internet.
Códigos de respuesta: Debes responder con un código HTTP 2xx(idealmente 200 OK) para confirmar la recepción del evento.
Importante
Si tu endpoint no responde con un código 2xx, Wompi reintentará el envío del evento hasta 3 veces adicionales.

Tipos de eventos disponibles
Wompi actualmente emite los siguientes eventos relacionados con los pagos:

Cambio de estado de un lote
payout.updated

Ejemplo de evento:

{
  "event": "payout.updated",
  "data": {
    "payout": {
      "id": "04a6e53d-a244-4140-ab9e-48fa541f9fe5",
      "reference": "ref_98765",
      "amountInCents": 7500000,
      "paymentType": "PAYROLL",
      "status": "TOTAL_PAYMENT",
      "totalTransactions": 3,
      "currency": "COP",
      "dispersionDatetime": "2025-05-14T10:30:00.000Z",
      "approvedAt": "2025-05-14T11:00:00.000Z",
      "createdAt": "2025-05-13T09:00:00.000Z"
    }
  },
  "signature": {
    "properties": ["payout.id", "payout.status", "payout.amountInCents"],
    "checksum": "639dc6bd2ac0104f090651c07773b6537f935623cf0ed04894f0687d4c9eebc7"
  },
  "timestamp": 1747673128600,
  "sentAt": "2025-05-15T15:00:00.000Z"
}

Cambio de estado de una transacción
transaction.updated

Ejemplo de evento:

{
  "event": "transaction.updated",
  "data": {
    "transaction": {
      "id": "04a6e53d-a244-4140-ab9e-48fa541f9fe5",
      "payoutId": "payout_12345",
      "amountInCents": 7500000,
      "status": "FAILED",
      "payee": {
        "name": "Juan Pérez",
        "document": "123456789",
        "bank": "BANCOLOMBIA",
        "accountType": "SAVINGS",
        "accountNumber": "1234567890",
        "email": "juan.perez@example.com"
      },
      "failureReason": {
        "code": "C01",
        "message": "La cuenta no existe o está inactiva"
      },
      "currency": "COP",
      "appliedAt": "2025-05-14T13:00:00.000Z",
      "createdAt": "2025-05-13T10:00:00.000Z"
    }
  },
  "signature": {
    "properties": [
      "transaction.id",
      "transaction.status",
      "transaction.amountInCents"
    ],
    "checksum": "82f0e769716170e202edfd348f604bd8461cdeeb416594cde563a890215a5282"
  },
  "timestamp": 1747673128600,
  "sentAt": "2025-05-15T15:00:00.000Z"
}

Seguridad: Validación de integridad
Cada evento enviado por Wompi incluye una firma criptográfica para que puedas validar su autenticidad y asegurarte de que no ha sido modificado en tránsito.

¿Dónde está la firma?: La firma se encuentra en dos lugares del evento:

En el header HTTP: X-Event-Checksum
En el body del evento: signature.checksum
La firma se genera a partir de una lista de propiedades (signature.properties) y el uso del secreto de eventos que puedes obtener desde la sección de programadores.

Obtener secreto de eventos
Un Secreto conocido únicamente por el comercio y Wompi, que está disponible en la opción programadores de pagos a terceros, bajo la sección Secretos para integración técnica. Este secreto debe ser custodiado con la máxima seguridad en tus servidores.

Secreto de integración

Pasos para validar la firma
Extrae las propiedades listadas en signature.properties, en el orden en que aparecen.
Concatena los valores como una cadena de texto, sin espacios ni separadores.
Concatena el campo timestamp.
Concatena tu secreto.
Genera el hash usando el algoritmo SHA256.
Compara el resultado con el valor de X-Event-Checksum o signature.checksum.
Si los valores coinciden, el evento es legítimo. Si no, debes rechazarlo y no procesarlo.

nota
Los properties pueden variar en el tiempo y en cada evento, por eso es muy importante que no los asumas como un arreglo fijo dentro de tu código, sino que siempre los extraigas del evento y utilices apropiadamente en cada validación.

Ejemplo
Validemos la firma del evento visto anteriormente transaction.updated

Paso 1: Concatena los valores de los datos del evento
En el objeto signature del evento debes concatenar el valor de los datos descritos en el campo properties. En este caso tenemos:

transaction.id: Cuyo valor es 04a6e53d-a244-4140-ab9e-48fa541f9fe5
transaction.status: Cuyo valor es FAILED
transaction.amountInCents: Cuyo valor es 7500000
El valor resultante de la concatenación de estos datos, respetando el orden especificados en el arreglo signature.properties es:

04a6e53d-a244-4140-ab9e-48fa541f9fe5FAILED7500000

Paso 2: Concatena el campo timestamp
A la concatenación de las propiedades mostradas en el Paso 1, debes concatenarle también el campo timestamp del evento, que en este caso es 1747673128600. El valor que deberías tener ahora en la cadena en este punto es:

04a6e53d-a244-4140-ab9e-48fa541f9fe5FAILED75000001747673128600

Paso 3: Concatena tu secreto
En este paso debes concatenar tu secreto al string que estás generando hasta este punto. Vamos a asumir, en este ejemplo, que tu secreto es:

prod_events_7b193c8afd7b47949f90d443cb1e1742

Recuerda
El secreto de eventos es distinto a la API Key

El resultado final de la concatenación debería ser:

04a6e53d-a244-4140-ab9e-48fa541f9fe5FAILED75000001747673128600prod_events_7b193c8afd7b47949f90d443cb1e1742

Paso 4: Usa SHA256 para generar el checksum
Con estos datos concatenados apropiadamente, es momento de generar el checksum usando SHA256. Pasando la cadena por este algoritmo se obtiene por ejemplo el siguiente resultado:

82f0e769716170e202edfd348f604bd8461cdeeb416594cde563a890215a5282

La manera en la que usa SHA256 para calcular este valor, varía dependiendo de cada lenguaje de programación. Sin embargo, el resultado debe ser siempre el mismo, dada la naturaleza de este algoritmo seguro de encripción asimétrica.

Paso 5: Compara tu checksum calculado con el proveído en el evento
Al generar tú mismo, el valor del checksum en tu servidor, puedes ahora compararlo con el que llegó en el evento. Si ambos son iguales entonces puedes estar seguro que la información presentada es legítima y enviada por Wompi, y no una suplantación de un tercero. De lo contrario, debes ignorar dicho evento.


referencias de api en postman json


  "info": {
    "_postman_id": "5daa8ab1-833f-45d2-b3db-fa085005906b",
    "name": "API Pública - Payouts",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    "_exporter_id": "39097919"
  },
  "item": [
    {
      "name": "Sandbox",
      "item": [
        {
          "name": "Sandbox Tools",
          "item": [
            {
              "name": "1. Recarga la cuenta bancaria para pruebas sandbox",
              "request": {
                "method": "POST",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "body": {
                  "mode": "raw",
                  "raw": "{\n  \"accountId\": \"$AccountID\",\n  \"amountInCents\": 2100000\n}",
                  "options": {
                    "raw": {
                      "language": "json"
                    }
                  }
                },
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/accounts/balance-recharge",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["accounts", "balance-recharge"]
                }
              },
              "response": []
            },
            {
              "name": "2. Reportes CSV",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/reports/presigned_url",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["reports", "presigned_url"],
                  "query": [
                    {
                      "key": "reportExecutionId",
                      "value": "_Id",
                      "disabled": true
                    },
                    {
                      "key": "reportIntegration",
                      "value": "payouts",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            }
          ]
        },
        {
          "name": "Recursos",
          "item": [
            {
              "name": "1. Bancos",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/banks",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["banks"]
                }
              },
              "response": []
            },
            {
              "name": "2. Cuentas",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/accounts",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["accounts"]
                }
              },
              "response": []
            },
            {
              "name": "3. Limites",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/limits",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["limits"]
                }
              },
              "response": []
            }
          ]
        },
        {
          "name": "Pagos",
          "item": [
            {
              "name": "1. Crear pago",
              "request": {
                "method": "POST",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "body": {
                  "mode": "raw",
                  "raw": "{\n    \"reference\": \"demo-reference\",\n    \"accountId\": \"WOMPI_ACCOUNT\",\n    \"paymentType\": \"PAYROLL\",\n    \"transactions\": [\n        {\n            \"legalIdType\": \"CC\",\n            \"legalId\": \"1234567890\",\n            \"bankId\": \"6e422ee9-6863-4882-a265-42258b410caa\",\n            \"accountType\": \"AHORROS\",\n            \"accountNumber\": \"43423123\",\n            \"name\": \"John Doe\",\n            \"amount\": 20000,\n            \"personType\": \"NATURAL\",\n            \"description\": \"description\",\n            \"phone\": \"44321323\",\n            \"email\": \"email@example.com\",\n            \"reference\": \"custom-reference\"\n        }\n    ]\n}",
                  "options": {
                    "raw": {
                      "language": "json"
                    }
                  }
                },
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/payouts",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["payouts"]
                }
              },
              "response": []
            },
            {
              "name": "2. Crear pago por archivo",
              "request": {
                "method": "POST",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "body": {
                  "mode": "formdata",
                  "formdata": [
                    {
                      "key": "reference",
                      "value": "demo-reference",
                      "type": "text"
                    },
                    {
                      "key": "accountId",
                      "value": "WOMPI_ACCOUNT",
                      "type": "text"
                    },
                    {
                      "key": "paymentType",
                      "value": "PAYROLL",
                      "type": "text"
                    },
                    {
                      "key": "file",
                      "type": "file",
                      "src": "/Users/a68211/Documents/Estandares/Wompi File/PAB_1030604363_240321_153020386.txt"
                    },
                    {
                      "key": "fileType",
                      "value": "PAB",
                      "type": "text"
                    }
                  ]
                },
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/payouts/file",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["payouts", "file"]
                }
              },
              "response": []
            }
          ]
        },
        {
          "name": "Consultas",
          "item": [
            {
              "name": "1. Consultar pagos",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/payouts",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["payouts"],
                  "query": [
                    {
                      "key": "page",
                      "value": "1",
                      "disabled": true
                    },
                    {
                      "key": "limit",
                      "value": "10",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            },
            {
              "name": "2. Consultar pagos por id",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/payouts/$PayoutID",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["payouts", "$PayoutID"]
                }
              },
              "response": []
            },
            {
              "name": "3. Consultar transacciones de un pago",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/payouts/$PayoutID/transactions",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["payouts", "$PayoutID", "transactions"],
                  "query": [
                    {
                      "key": "page",
                      "value": "1",
                      "disabled": true
                    },
                    {
                      "key": "limit",
                      "value": "10",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            },
            {
              "name": "4. Consultar transacción por id",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/payouts/$PayoutID/transactions/$TransactionID",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": [
                    "payouts",
                    "$PayoutID",
                    "transactions",
                    "$TransactionID"
                  ]
                }
              },
              "response": []
            },
            {
              "name": "5. Consultar transacción por referencia personalizada",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID-SANDBOX}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY-SANDBOX}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN-SANDBOX}}/transactions/$Reference",
                  "host": ["{{DOMAIN-SANDBOX}}"],
                  "path": ["transactions", "$Reference"],
                  "query": [
                    {
                      "key": "page",
                      "value": "1",
                      "disabled": true
                    },
                    {
                      "key": "limit",
                      "value": "10",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            }
          ]
        }
      ]
    },
    {
      "name": "Producción",
      "item": [
        {
          "name": "Recursos",
          "item": [
            {
              "name": "1. Bancos",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/banks",
                  "host": ["{{DOMAIN}}"],
                  "path": ["banks"]
                }
              },
              "response": []
            },
            {
              "name": "2. Cuentas",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/accounts",
                  "host": ["{{DOMAIN}}"],
                  "path": ["accounts"]
                }
              },
              "response": []
            },
            {
              "name": "3. Limites",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/limits",
                  "host": ["{{DOMAIN}}"],
                  "path": ["limits"]
                }
              },
              "response": []
            }
          ]
        },
        {
          "name": "Pagos",
          "item": [
            {
              "name": "1. Crear pago",
              "request": {
                "method": "POST",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "body": {
                  "mode": "raw",
                  "raw": "{\n    \"reference\": \"demo-reference\",\n    \"accountId\": \"WOMPI_ACCOUNT\",\n    \"paymentType\": \"PAYROLL\",\n    \"transactions\": [\n        {\n            \"legalIdType\": \"CC\",\n            \"legalId\": \"1234567890\",\n            \"bankId\": \"6e422ee9-6863-4882-a265-42258b410caa\",\n            \"accountType\": \"AHORROS\",\n            \"accountNumber\": \"43423123\",\n            \"name\": \"John Doe\",\n            \"amount\": 20000,\n            \"personType\": \"NATURAL\",\n            \"description\": \"description\",\n            \"phone\": \"44321323\",\n            \"email\": \"email@example.com\",\n            \"reference\": \"custom-reference\"\n        }\n    ]\n}",
                  "options": {
                    "raw": {
                      "language": "json"
                    }
                  }
                },
                "url": {
                  "raw": "{{DOMAIN}}/payouts",
                  "host": ["{{DOMAIN}}"],
                  "path": ["payouts"]
                }
              },
              "response": []
            },
            {
              "name": "2. Crear pago por archivo",
              "request": {
                "method": "POST",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "body": {
                  "mode": "formdata",
                  "formdata": [
                    {
                      "key": "reference",
                      "value": "demo-reference",
                      "type": "text"
                    },
                    {
                      "key": "accountId",
                      "value": "WOMPI_ACCOUNT",
                      "type": "text"
                    },
                    {
                      "key": "paymentType",
                      "value": "PAYROLL",
                      "type": "text"
                    },
                    {
                      "key": "file",
                      "type": "file",
                      "src": "/Users/a68211/Documents/Estandares/Wompi File/PAB_1030604363_240321_153020386.txt"
                    },
                    {
                      "key": "fileType",
                      "value": "PAB",
                      "type": "text"
                    }
                  ]
                },
                "url": {
                  "raw": "{{DOMAIN}}/payouts/file",
                  "host": ["{{DOMAIN}}"],
                  "path": ["payouts", "file"]
                }
              },
              "response": []
            }
          ]
        },
        {
          "name": "Consultas",
          "item": [
            {
              "name": "1. Consultar pagos",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/payouts",
                  "host": ["{{DOMAIN}}"],
                  "path": ["payouts"],
                  "query": [
                    {
                      "key": "page",
                      "value": "1",
                      "disabled": true
                    },
                    {
                      "key": "limit",
                      "value": "10",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            },
            {
              "name": "2. Consultar pagos por id",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/payouts/$PayoutID",
                  "host": ["{{DOMAIN}}"],
                  "path": ["payouts", "$PayoutID"]
                }
              },
              "response": []
            },
            {
              "name": "3. Consultar transacciones de un pago",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/payouts/$PayoutID/transactions",
                  "host": ["{{DOMAIN}}"],
                  "path": ["payouts", "$PayoutID", "transactions"],
                  "query": [
                    {
                      "key": "page",
                      "value": "1",
                      "disabled": true
                    },
                    {
                      "key": "limit",
                      "value": "10",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            },
            {
              "name": "4. Consultar transacción por id",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/payouts/$PayoutID/transactions/$TransactionID",
                  "host": ["{{DOMAIN}}"],
                  "path": [
                    "payouts",
                    "$PayoutID",
                    "transactions",
                    "$TransactionID"
                  ]
                }
              },
              "response": []
            },
            {
              "name": "5. Consultar transacción por referencia personalizada",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/transactions/$Reference",
                  "host": ["{{DOMAIN}}"],
                  "path": ["transactions", "$Reference"],
                  "query": [
                    {
                      "key": "page",
                      "value": "1",
                      "disabled": true
                    },
                    {
                      "key": "limit",
                      "value": "10",
                      "disabled": true
                    }
                  ]
                }
              },
              "response": []
            },
            {
              "name": "6. Consultar disponibilidad",
              "request": {
                "method": "GET",
                "header": [
                  {
                    "key": "user-principal-id",
                    "value": "{{USER-PRINCIPAL-ID}}",
                    "type": "text"
                  },
                  {
                    "key": "x-api-key",
                    "value": "{{X-API-KEY}}",
                    "type": "text"
                  }
                ],
                "url": {
                  "raw": "{{DOMAIN}}/health",
                  "host": ["{{DOMAIN}}"],
                  "path": ["health"]
                }
              },
              "response": []
            }
          ]
        }
      ]
    }
  ]
}



Errores en el API
Cuando se genere un error al crear los lotes, se presentará un error con el siguiente formato:

{
  "code": "EXC_001",
  "message": "Se presentó error interno procesando la solicitud."
}

Listado de errores
A continuación se listan los errores posibles con su respectivo mensaje.

Código	Código HTTP	Mensaje
EXC_001	500	Se presentó error interno procesando la solicitud.
EXC_002	400	Se presentó error de negocio procesando la solicitud.
EXC_008	400	Saldo insuficiente para procesar el lote.
EXC_017	400	Se ha alcanzado el límite diario.
EXC_018	400	Se ha alcanzado el límite de transacciones del plan.
EXC_019	400	No se puede realizar el pago con la cuenta elegida.
EXC_022	409	Idempotency key ya fue procesada.