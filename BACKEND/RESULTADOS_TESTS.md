# Análisis de Resultados — Suite de Tests & Benchmark API Ambulancias SOAT

> **Ejecutado:** 28 de abril de 2026  
> **Entorno:** Contenedor Docker `backend` (Django + SQLite de prueba)  
> **Comando tests:** `docker exec backend python manage.py test ambulancias usuarios --verbosity=2`  
> **Comando benchmark:** `docker exec backend python scripts/benchmark_endpoints.py`  
> **Duración suite:** 18.870 s | **Peticiones benchmark:** 620 (20 por endpoint)

---

## 1. Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| Total de tests | **146** |
| Pasaron (OK) | **146** |
| Fallaron (FAIL) | **0** |
| Errores (ERROR) | 0 |
| Tasa de éxito | **100 %** |
| Tiempo de ejecución suite | 18.870 s |
| Endpoints medidos en benchmark | 31 |
| AVG global de respuesta | 2.70 ms |

### Datos para gráfico — Resumen global (Pie / Donut)

```csv
categoria,cantidad,porcentaje
PASS,146,100.0
FAIL,0,0.0
```

---

## 2. Resultados por Módulo

| Módulo | Tests | Pasaron | Fallaron | Tasa |
|---|---|---|---|---|
| `ambulancias` | 56 | 56 | 0 | 100.00 % |
| `usuarios` | 90 | 90 | 0 | 100.00 % |
| **Total** | **146** | **146** | **0** | **100.00 %** |

### Datos para gráfico — Tests por módulo (Grouped Bar)

```csv
modulo,pass,fail
ambulancias,56,0
usuarios,90,0
```

---

## 3. Resultados por Suite (Clase de Test)

### 3.1 Módulo `ambulancias`

| Suite | Tests | PASS | FAIL | Endpoint cubierto |
|---|---|---|---|---|
| `OrganizacionTests` | 8 | 8 | 0 | `GET/POST/PUT /api/organizacion/` |
| `SedeListTests` | 5 | 5 | 0 | `GET/POST /api/sedes/` |
| `SedeDetalleTests` | 6 | 6 | 0 | `GET/PUT/DELETE /api/sedes/<id>/` |
| `AmbulanciaListTests` | 7 | 7 | 0 | `GET/POST /api/ambulancias/` |
| `AmbulanciaDetalleTests` | 7 | 7 | 0 | `GET/PUT/DELETE /api/ambulancias/<id>/` |
| `SOATListTests` | 11 | 11 | 0 | `GET/POST /api/soat/` |
| `SOATDetalleTests` | 7 | 7 | 0 | `GET/PUT/DELETE /api/soat/<id>/` |
| `ExportarSOATTests` | 5 | 5 | 0 | `GET /api/soat/<id>/exportar/` |
| **Subtotal** | **56** | **56** | **0** | |

### 3.2 Módulo `usuarios`

| Suite | Tests | PASS | FAIL | Endpoint cubierto |
|---|---|---|---|---|
| `PerfilTests` | 9 | 9 | 0 | `GET/PATCH /user/perfil/` |
| `RegisterTests` | 10 | 10 | 0 | `GET/POST/PUT /user/register/<id>/` |
| `RegisterTemporalTests` | 4 | 4 | 0 | `POST /user/registerTemporal/` |
| `RegistrarMasivoTests` | 5 | 5 | 0 | `POST /user/registrar-masivo/` |
| `ListaUsuariosTests` | 6 | 6 | 0 | `GET /user/lista-usuarios/` |
| `CargoNivelRegionalViewTests` | 3 | 3 | 0 | `GET /user/cargo-Nivel-Regional/` |
| `FiltrarUsuariosTests` | 6 | 6 | 0 | `GET /user/filtrar-usuarios/` |
| `CambiarEstadoUsuarioTests` | 11 | 11 | 0 | `POST/PATCH /user/cambiar-estado-usuario/` |
| `ActualizarRolUsuarioTests` | 6 | 6 | 0 | `PATCH /user/actualizar-rol-usuario/<id>/` |
| `DatosCargoTests` | 11 | 11 | 0 | `GET/POST/PUT/DELETE /user/Cargo/` |
| `DatosNivelTests` | 8 | 8 | 0 | `GET/POST/PUT/DELETE /user/Nivel/` |
| `DatosRegionTests` | 8 | 8 | 0 | `GET/POST/PUT/DELETE /user/Region/` |
| `ReporteUsuariosTests` | 3 | 3 | 0 | `GET /user/reporte-usuarios/` |
| **Subtotal** | **90** | **90** | **0** | |

### Datos para gráfico — Tests por suite (Horizontal Stacked Bar)

```csv
suite,pass,fail,total
OrganizacionTests,8,0,8
SedeListTests,5,0,5
SedeDetalleTests,6,0,6
AmbulanciaListTests,7,0,7
AmbulanciaDetalleTests,7,0,7
SOATListTests,11,0,11
SOATDetalleTests,7,0,7
ExportarSOATTests,5,0,5
PerfilTests,9,0,9
RegisterTests,10,0,10
RegisterTemporalTests,4,0,4
RegistrarMasivoTests,5,0,5
ListaUsuariosTests,6,0,6
CargoNivelRegionalViewTests,3,0,3
FiltrarUsuariosTests,6,0,6
CambiarEstadoUsuarioTests,11,0,11
ActualizarRolUsuarioTests,6,0,6
DatosCargoTests,11,0,11
DatosNivelTests,8,0,8
DatosRegionTests,8,0,8
ReporteUsuariosTests,3,0,3
```

---

## 4. Resultados por Método HTTP

| Método HTTP | Tests | PASS | FAIL |
|---|---|---|---|
| GET | 54 | 54 | 0 |
| POST | 44 | 44 | 0 |
| PUT | 20 | 20 | 0 |
| DELETE | 16 | 16 | 0 |
| PATCH | 12 | 12 | 0 |
| **Total** | **146** | **146** | **0** |

### Datos para gráfico — Tests por método HTTP (Stacked Bar)

```csv
metodo,pass,fail
GET,54,0
POST,44,0
PUT,20,0
DELETE,16,0
PATCH,12,0
```

---

## 5. Resultados por Categoría Funcional

| Categoría | Tests | PASS | FAIL |
|---|---|---|---|
| Autenticación (bloqueo 401) | 16 | 16 | 0 |
| Lectura de datos (GET 200/404) | 38 | 38 | 0 |
| Creación de recursos (POST 201) | 22 | 22 | 0 |
| Actualización (PUT/PATCH 200) | 20 | 20 | 0 |
| Eliminación (DELETE 200) | 9 | 9 | 0 |
| Validación de entrada (400) | 27 | 27 | 0 |
| Búsqueda y paginación | 9 | 9 | 0 |
| Exportación de archivos | 5 | 5 | 0 |
| **Total** | **146** | **146** | **0** |

### Datos para gráfico — Tests por categoría (Radar / Polar Area)

```csv
categoria,pass,fail,total
Autenticacion_401,16,0,16
Lectura_GET,38,0,38
Creacion_POST,22,0,22
Actualizacion_PUT_PATCH,20,0,20
Eliminacion_DELETE,9,0,9
Validacion_400,27,0,27
Busqueda_Paginacion,9,0,9
Exportacion,5,0,5
```

---

## 6. Tasa de Éxito por Suite

### Datos para gráfico — Tasa de éxito % por suite (Bar)

```csv
suite,tasa_exito
OrganizacionTests,100.0
SedeListTests,100.0
SedeDetalleTests,100.0
AmbulanciaListTests,100.0
AmbulanciaDetalleTests,100.0
SOATListTests,100.0
SOATDetalleTests,100.0
ExportarSOATTests,100.0
PerfilTests,100.0
RegisterTests,100.0
RegisterTemporalTests,100.0
RegistrarMasivoTests,100.0
ListaUsuariosTests,100.0
CargoNivelRegionalViewTests,100.0
FiltrarUsuariosTests,100.0
CambiarEstadoUsuarioTests,100.0
ActualizarRolUsuarioTests,100.0
DatosCargoTests,100.0
DatosNivelTests,100.0
DatosRegionTests,100.0
ReporteUsuariosTests,100.0
```

---

## 7. Tiempo de Ejecución de la Suite

| Dato | Valor |
|---|---|
| Tiempo total de suite | 18.870 s |
| Promedio por test | ~0.129 s |
| Tests por segundo | ~7.7 tests/s |

> El tiempo incluye creación y destrucción de la BD SQLite de prueba y la aplicación de todas las migraciones Django.

---

## 8. Tiempos de Respuesta por Endpoint (Benchmark)

> **Metodología:** 20 peticiones por endpoint usando el cliente de pruebas Django (sin latencia de red — mide solo procesamiento ORM + vista). Todos los endpoints retornan 200/201.  
> **Unidades:** milisegundos (ms) | **n = 20 peticiones por endpoint**

### 8.1 Tabla completa

| Endpoint | Método | Status | MIN | AVG | MEDIAN | P95 | MAX | STDEV |
|---|---|---|---|---|---|---|---|---|
| Organizacion - GET singleton | GET | 200 | 0.80 | 11.04 | 0.89 | 201.94 | 201.94 | 44.93 |
| Organizacion - POST crear/actualizar | POST | 200 | 1.64 | 1.93 | 1.87 | 2.56 | 2.56 | 0.24 |
| Sedes - GET lista | GET | 200 | 2.37 | 2.85 | 2.70 | 4.02 | 4.02 | 0.50 |
| Sedes - POST crear | POST | 201 | 3.55 | 5.69 | 4.11 | 27.50 | 27.50 | 5.53 |
| Sedes - GET detalle | GET | 200 | 0.83 | 0.98 | 0.93 | 1.56 | 1.56 | 0.20 |
| Sedes - PUT actualizar | PUT | 200 | 1.27 | 1.66 | 1.39 | 5.46 | 5.46 | 0.92 |
| Ambulancias - GET lista | GET | 200 | 1.33 | 1.50 | 1.46 | 1.97 | 1.97 | 0.15 |
| Ambulancias - POST crear | POST | 201 | 4.09 | 5.06 | 4.91 | 7.25 | 7.25 | 0.75 |
| Ambulancias - GET detalle | GET | 200 | 1.01 | 1.17 | 1.12 | 1.72 | 1.72 | 0.16 |
| Ambulancias - PUT actualizar | PUT | 200 | 1.75 | 2.18 | 1.96 | 6.22 | 6.22 | 0.97 |
| SOAT - GET lista | GET | 200 | 1.60 | 1.89 | 1.79 | 3.34 | 3.34 | 0.38 |
| SOAT - GET lista paginada | GET | 200 | 1.59 | 1.88 | 1.81 | 2.75 | 2.75 | 0.27 |
| SOAT - GET busqueda | GET | 200 | 1.61 | 1.84 | 1.80 | 2.17 | 2.17 | 0.14 |
| SOAT - GET detalle | GET | 200 | 1.52 | 1.84 | 1.83 | 2.87 | 2.87 | 0.32 |
| SOAT - PUT actualizar | PUT | 200 | 2.71 | 3.31 | 3.07 | 7.40 | 7.40 | 1.02 |
| SOAT - GET exportar TXT | GET | 200 | 1.04 | 1.28 | 1.16 | 2.41 | 2.41 | 0.35 |
| Perfil - GET propio | GET | 200 | 0.91 | 1.07 | 1.01 | 1.50 | 1.50 | 0.16 |
| Lista Usuarios - GET | GET | 200 | 1.39 | 1.57 | 1.53 | 1.89 | 1.89 | 0.14 |
| Filtrar Usuarios - GET sin filtro | GET | 200 | 1.64 | 1.95 | 1.92 | 2.54 | 2.54 | 0.22 |
| Filtrar Usuarios - GET por nombre | GET | 200 | 1.63 | 1.84 | 1.84 | 2.39 | 2.39 | 0.17 |
| Cargo/Nivel/Regional - GET | GET | 200 | 1.74 | 2.04 | 2.00 | 2.83 | 2.83 | 0.24 |
| Cargo - GET lista | GET | 200 | 1.14 | 1.29 | 1.26 | 1.56 | 1.56 | 0.12 |
| Cargo - POST crear | POST | 201 | 3.20 | 4.43 | 4.31 | 5.50 | 5.50 | 0.68 |
| Cargo - PUT actualizar | PUT | 200 | 1.15 | 1.49 | 1.28 | 4.49 | 4.49 | 0.72 |
| Nivel - GET lista | GET | 200 | 1.19 | 1.40 | 1.38 | 1.75 | 1.75 | 0.17 |
| Nivel - POST crear | POST | 201 | 3.68 | 4.83 | 4.75 | 6.31 | 6.31 | 0.65 |
| Nivel - PUT actualizar | PUT | 200 | 1.17 | 1.51 | 1.33 | 3.96 | 3.96 | 0.59 |
| Region - GET lista | GET | 200 | 1.14 | 1.33 | 1.26 | 1.92 | 1.92 | 0.19 |
| Region - POST crear | POST | 201 | 3.66 | 4.69 | 4.61 | 6.70 | 6.70 | 0.71 |
| Region - PUT actualizar | PUT | 200 | 1.32 | 2.16 | 1.85 | 4.55 | 4.55 | 0.81 |
| Reporte Usuarios - GET Excel | GET | 200 | 3.99 | 6.10 | 5.38 | 12.26 | 12.26 | 2.20 |

> **Nota Organizacion GET:** cold-start de ORM eleva el AVG. El MEDIAN (0.89 ms) es el valor representativo de estado estacionario.

---

### 8.2 Resumen estadístico global del benchmark

| Métrica | Valor |
|---|---|
| Endpoints medidos | 31 |
| Total peticiones | 620 |
| AVG global (todos los endpoints) | **2.70 ms** |
| Endpoint más rápido (AVG) | Sedes - GET detalle — **0.98 ms** |
| Endpoint más lento (AVG) | Organizacion - GET singleton — **11.04 ms** (cold-start) |
| Endpoint más lento sostenido (MEDIAN) | Reporte Usuarios - GET Excel — **5.38 ms** |
| POST más lento (AVG) | Sedes - POST crear — **5.69 ms** |

---

### 8.3 Ranking AVG ascendente — datos para gráfico Horizontal Bar

```csv
endpoint,metodo,avg_ms,status
Sedes GET detalle,GET,0.98,200
Perfil GET propio,GET,1.07,200
Ambulancias GET detalle,GET,1.17,200
SOAT GET exportar TXT,GET,1.28,200
Cargo GET lista,GET,1.29,200
Region GET lista,GET,1.33,200
Nivel GET lista,GET,1.40,200
Ambulancias GET lista,GET,1.50,200
Sedes PUT actualizar,PUT,1.66,200
Lista Usuarios GET,GET,1.57,200
Cargo PUT actualizar,PUT,1.49,200
Nivel PUT actualizar,PUT,1.51,200
SOAT GET busqueda,GET,1.84,200
SOAT GET detalle,GET,1.84,200
Filtrar Usuarios GET nombre,GET,1.84,200
SOAT GET lista paginada,GET,1.88,200
SOAT GET lista,GET,1.89,200
Organizacion POST,POST,1.93,200
Filtrar Usuarios GET sin filtro,GET,1.95,200
Cargo Nivel Regional GET,GET,2.04,200
Region PUT actualizar,PUT,2.16,200
Ambulancias PUT actualizar,PUT,2.18,200
Sedes GET lista,GET,2.85,200
SOAT PUT actualizar,PUT,3.31,200
Cargo POST crear,POST,4.43,201
Region POST crear,POST,4.69,201
Nivel POST crear,POST,4.83,201
Ambulancias POST crear,POST,5.06,201
Sedes POST crear,POST,5.69,201
Reporte Usuarios GET Excel,GET,6.10,200
Organizacion GET singleton,GET,11.04,200
```

---

### 8.4 Comparativa por método HTTP — datos para Grouped Bar

```csv
metodo,endpoints,avg_ms_global,min_avg_ms,max_avg_ms
GET,20,2.33,0.98,11.04
POST,6,4.39,1.93,5.69
PUT,5,2.06,1.49,3.31
```

---

### 8.5 AVG vs P95 — datos para gráfico de dispersión / Dual Bar

```csv
endpoint,metodo,avg_ms,p95_ms,diferencia_ms
Organizacion GET singleton,GET,11.04,201.94,190.90
Sedes POST crear,POST,5.69,27.50,21.81
Reporte Usuarios GET Excel,GET,6.10,12.26,6.16
SOAT PUT actualizar,PUT,3.31,7.40,4.09
Ambulancias POST crear,POST,5.06,7.25,2.19
Ambulancias PUT actualizar,PUT,2.18,6.22,4.04
Sedes PUT actualizar,PUT,1.66,5.46,3.80
Nivel POST crear,POST,4.83,6.31,1.48
Region POST crear,POST,4.69,6.70,2.01
Cargo POST crear,POST,4.43,5.50,1.07
Cargo PUT actualizar,PUT,1.49,4.49,3.00
Nivel PUT actualizar,PUT,1.51,3.96,2.45
Region PUT actualizar,PUT,2.16,4.55,2.39
SOAT GET lista,GET,1.89,3.34,1.45
Sedes GET lista,GET,2.85,4.02,1.17
Cargo Nivel Regional GET,GET,2.04,2.83,0.79
SOAT GET detalle,GET,1.84,2.87,1.03
SOAT GET lista paginada,GET,1.88,2.75,0.87
Filtrar Usuarios GET sin filtro,GET,1.95,2.54,0.59
Filtrar Usuarios GET nombre,GET,1.84,2.39,0.55
SOAT GET busqueda,GET,1.84,2.17,0.33
SOAT GET exportar TXT,GET,1.28,2.41,1.13
Perfil GET propio,GET,1.07,1.50,0.43
Lista Usuarios GET,GET,1.57,1.89,0.32
Nivel GET lista,GET,1.40,1.75,0.35
Region GET lista,GET,1.33,1.92,0.59
Ambulancias GET lista,GET,1.50,1.97,0.47
Organizacion POST,POST,1.93,2.56,0.63
Ambulancias GET detalle,GET,1.17,1.72,0.55
Cargo GET lista,GET,1.29,1.56,0.27
Sedes GET detalle,GET,0.98,1.56,0.58
```

---

### 8.6 MIN / AVG / MEDIAN / P95 por endpoint — datos para gráfico Line / Multi-series Bar

```csv
endpoint,metodo,min_ms,avg_ms,median_ms,p95_ms,stdev_ms
Sedes GET detalle,GET,0.83,0.98,0.93,1.56,0.20
Perfil GET propio,GET,0.91,1.07,1.01,1.50,0.16
Ambulancias GET detalle,GET,1.01,1.17,1.12,1.72,0.16
SOAT GET exportar TXT,GET,1.04,1.28,1.16,2.41,0.35
Cargo GET lista,GET,1.14,1.29,1.26,1.56,0.12
Region GET lista,GET,1.14,1.33,1.26,1.92,0.19
Nivel GET lista,GET,1.19,1.40,1.38,1.75,0.17
Ambulancias GET lista,GET,1.33,1.50,1.46,1.97,0.15
Lista Usuarios GET,GET,1.39,1.57,1.53,1.89,0.14
Cargo PUT actualizar,PUT,1.15,1.49,1.28,4.49,0.72
Nivel PUT actualizar,PUT,1.17,1.51,1.33,3.96,0.59
Sedes PUT actualizar,PUT,1.27,1.66,1.39,5.46,0.92
SOAT GET busqueda,GET,1.61,1.84,1.80,2.17,0.14
SOAT GET detalle,GET,1.52,1.84,1.83,2.87,0.32
Filtrar Usuarios GET nombre,GET,1.63,1.84,1.84,2.39,0.17
SOAT GET lista paginada,GET,1.59,1.88,1.81,2.75,0.27
SOAT GET lista,GET,1.60,1.89,1.79,3.34,0.38
Organizacion POST,POST,1.64,1.93,1.87,2.56,0.24
Filtrar Usuarios GET sin filtro,GET,1.64,1.95,1.92,2.54,0.22
Cargo Nivel Regional GET,GET,1.74,2.04,2.00,2.83,0.24
Region PUT actualizar,PUT,1.32,2.16,1.85,4.55,0.81
Ambulancias PUT actualizar,PUT,1.75,2.18,1.96,6.22,0.97
Sedes GET lista,GET,2.37,2.85,2.70,4.02,0.50
SOAT PUT actualizar,PUT,2.71,3.31,3.07,7.40,1.02
Cargo POST crear,POST,3.20,4.43,4.31,5.50,0.68
Region POST crear,POST,3.66,4.69,4.61,6.70,0.71
Nivel POST crear,POST,3.68,4.83,4.75,6.31,0.65
Ambulancias POST crear,POST,4.09,5.06,4.91,7.25,0.75
Sedes POST crear,POST,3.55,5.69,4.11,27.50,5.53
Reporte Usuarios GET Excel,GET,3.99,6.10,5.38,12.26,2.20
Organizacion GET singleton,GET,0.80,11.04,0.89,201.94,44.93
```

---

### 8.7 STDEV — endpoints con mayor variabilidad (datos para gráfico Bar descendente)

```csv
endpoint,metodo,stdev_ms
Organizacion GET singleton,GET,44.93
Sedes POST crear,POST,5.53
Reporte Usuarios GET Excel,GET,2.20
SOAT PUT actualizar,PUT,1.02
Ambulancias PUT actualizar,PUT,0.97
Sedes PUT actualizar,PUT,0.92
Region PUT actualizar,PUT,0.81
Ambulancias POST crear,POST,0.75
Cargo PUT actualizar,PUT,0.72
Region POST crear,POST,0.71
Nivel POST crear,POST,0.65
Cargo POST crear,POST,0.68
Nivel PUT actualizar,PUT,0.59
Sedes GET lista,GET,0.50
SOAT GET lista,GET,0.38
SOAT GET exportar TXT,GET,0.35
SOAT GET detalle,GET,0.32
Filtrar Usuarios GET sin filtro,GET,0.22
Nivel GET lista,GET,0.17
Filtrar Usuarios GET nombre,GET,0.17
SOAT GET lista paginada,GET,0.27
Cargo Nivel Regional GET,GET,0.24
Organizacion POST,POST,0.24
Perfil GET propio,GET,0.16
Ambulancias GET detalle,GET,0.16
Region GET lista,GET,0.19
SOAT GET busqueda,GET,0.14
Lista Usuarios GET,GET,0.14
Cargo GET lista,GET,0.12
Ambulancias GET lista,GET,0.15
Sedes GET detalle,GET,0.20
```

---

## 9. Gráficos Recomendados

| # | Tipo de gráfico | Sección de datos | Objetivo |
|---|---|---|---|
| 1 | **Pie / Donut** | Sección 1 | PASS vs FAIL global |
| 2 | **Grouped Bar** | Sección 2 | Tests por módulo |
| 3 | **Horizontal Stacked Bar** | Sección 3 | Tests PASS/FAIL por suite |
| 4 | **Stacked Bar** | Sección 4 | Tests por método HTTP |
| 5 | **Radar / Polar Area** | Sección 5 | Tests por categoría funcional |
| 6 | **Bar** | Sección 6 | Tasa de éxito % por suite |
| 7 | **Horizontal Bar** | Sección 8.3 | Ranking de latencia AVG por endpoint |
| 8 | **Grouped Bar** | Sección 8.4 | AVG global GET vs POST vs PUT |
| 9 | **Dual Bar / Scatter** | Sección 8.5 | AVG vs P95 — detectar variabilidad |
| 10 | **Multi-series Line** | Sección 8.6 | MIN / AVG / MEDIAN / P95 por endpoint |
| 11 | **Bar descendente** | Sección 8.7 | Endpoints con mayor variabilidad (STDEV) |

---

## 10. Conclusiones

1. **146/146 tests pasan (100 %)** — la suite está verde sin ningún fallo.
2. **Cobertura completa en ambos módulos** — `ambulancias` (56 tests) y `usuarios` (90 tests) cubren todos sus endpoints: autenticación, CRUD, paginación, búsqueda, exportación CSV/Excel y registro masivo.
3. **Tiempos de respuesta excelentes** — AVG global de 2.70 ms. Todos los GETs simples responden en menos de 2 ms (MEDIAN).
4. **Los POST con escritura a BD** tienen AVG entre 4–6 ms, con picos P95 de hasta 27 ms en Sedes POST (primera inserción con índices fríos).
5. **Organizacion GET singleton** presenta un AVG alto (11 ms) por cold-start del ORM; su MEDIAN real es 0.89 ms — no representa un problema de rendimiento.
6. **Reporte Usuarios GET Excel** es el endpoint más lento de forma sostenida (AVG 6.10 ms, MEDIAN 5.38 ms) por la generación del archivo `xlsx` en memoria.
7. **Alta estabilidad general** — 27 de 31 endpoints tienen STDEV < 1 ms. Solo Organizacion GET y Sedes POST muestran variabilidad alta (cold-start).
