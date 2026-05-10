"""
benchmark_endpoints.py
======================
Mide los tiempos de respuesta de cada endpoint de la API usando el
cliente de pruebas de Django (sin red real — mide solo el procesamiento
de la vista + ORM).

Uso (dentro del contenedor):
    python scripts/benchmark_endpoints.py

Salida: tabla por consola + archivo CSV en /tmp/benchmark_results.csv
"""

import os
import sys
import time
import csv
import io
import statistics

# ── Bootstrap Django ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIClient

from ambulancias.models import Organizacion, Sede, Ambulancia, RegistroSOAT
from usuarios.models import Usuarios, Colaboradores, Cargo, Niveles, Regional

# ── Configuración ─────────────────────────────────────────────────────────────
REPETICIONES = 20          # peticiones por endpoint
OUTPUT_CSV = "/tmp/benchmark_results.csv"

# ── Helpers de fixture ────────────────────────────────────────────────────────

def _crear_usuario(usuario="bench_usr", tipo=4):
    if Usuarios.objects.filter(usuario=usuario).exists():
        return Usuarios.objects.get(usuario=usuario)
    # Crear colaborador asociado para que /user/perfil/ funcione
    cargo, _ = Cargo.objects.get_or_create(nombrecargo="BenchCargo", defaults={"estadocargo": 1})
    nivel, _ = Niveles.objects.get_or_create(nombrenivel="BenchNivel", defaults={"estadonivel": 1})
    regional, _ = Regional.objects.get_or_create(nombreregional="BenchRegional", defaults={"estadoregional": 1})
    colab = Colaboradores.objects.create(
        cccolaborador="00000001",
        nombrecolaborador="Bench",
        apellidocolaborador="User",
        correocolaborador="bench@bench.com",
        telefocolaborador="3000000000",
        cargocolaborador=cargo,
        nivelcolaborador=nivel,
        regionalcolab=regional,
        estadocolaborador=1,
    )
    u = Usuarios(usuario=usuario, tipousuario=tipo, estadousuario=1, idcolaboradoru=colab)
    u.set_password("BenchPass@1234")
    u.save()
    return u


def _crear_sede():
    s, _ = Sede.objects.get_or_create(
        nombre="Sede Benchmark",
        defaults=dict(
            direccion="Av. Benchmark 100",
            telefono="3001000000",
            responsable="Bench User",
            activa=True,
        ),
    )
    return s


def _crear_ambulancia(sede):
    a, _ = Ambulancia.objects.get_or_create(
        placa="BCH001",
        defaults=dict(tipo="BAT", sede=sede, estado=1),
    )
    return a


def _crear_soat(sede, amb, user):
    return RegistroSOAT.objects.create(
        placa_ambulancia=amb.placa,
        tipo_ambulancia="BAT",
        nombre_paciente="Bench Paciente",
        documento_paciente=str(int(time.time() * 1000))[-8:],
        tipo_documento="CC",
        ambulancia=amb,
        sede=sede,
        registrado_por=user,
    )


def _crear_cargo():
    c, _ = Cargo.objects.get_or_create(nombrecargo="Benchmark Cargo", defaults=dict(estadocargo=1))
    return c


def _crear_nivel():
    n, _ = Niveles.objects.get_or_create(nombrenivel="Benchmark Nivel", defaults=dict(estadonivel=1))
    return n


def _crear_regional():
    r, _ = Regional.objects.get_or_create(nombreregional="Benchmark Regional", defaults=dict(estadoregional=1))
    return r


# ── Medición ──────────────────────────────────────────────────────────────────

_BENCH_RUN = str(int(time.time()))[-3:]   # 3 chars únicos por ejecución
_contador = [0]

def _resolver_payload(data):
    """Reemplaza '{}' con un identificador único por ejecución + contador (máx 6 chars)."""
    if data is None:
        return None
    _contador[0] += 1
    uniq = f"{_BENCH_RUN}{_contador[0]:03d}"   # ej: "321001" — 6 chars
    return {
        k: v.replace("{}", uniq) if isinstance(v, str) and "{}" in v else v
        for k, v in data.items()
    }


def medir(client, metodo, path, data=None):
    """Ejecuta REPETICIONES peticiones y retorna estadísticas (ms)."""
    tiempos = []
    ultimo_status = None
    fn = getattr(client, metodo)

    for _ in range(REPETICIONES):
        payload = _resolver_payload(data)
        t0 = time.perf_counter()
        if payload is not None:
            resp = fn(path, payload, content_type="application/json")
        else:
            resp = fn(path)
        t1 = time.perf_counter()
        tiempos.append((t1 - t0) * 1000)
        ultimo_status = resp.status_code

    return {
        "min": round(min(tiempos), 2),
        "max": round(max(tiempos), 2),
        "avg": round(statistics.mean(tiempos), 2),
        "median": round(statistics.median(tiempos), 2),
        "p95": round(sorted(tiempos)[int(len(tiempos) * 0.95)], 2),
        "stdev": round(statistics.stdev(tiempos) if len(tiempos) > 1 else 0, 2),
        "status": ultimo_status,
        "n": REPETICIONES,
    }


# ── Definición de escenarios ──────────────────────────────────────────────────

def definir_escenarios(sede, amb, soat, user, cargo, nivel, regional):
    sid = sede.idsede
    aid = amb.idambulancia
    rid = soat.idregistro
    cid = cargo.idcargo
    nid = nivel.idnivel
    regid = regional.idregional

    return [
        # ─── ambulancias ──────────────────────────────────────────────────────
        ("GET",    "/api/organizacion/",                     None,   "Organizacion - GET singleton",           "ambulancias"),
        ("POST",   "/api/organizacion/",                     {"nombre": "Org Bench", "nit": "900-1"},
                                                                     "Organizacion - POST crear/actualizar",   "ambulancias"),
        ("GET",    "/api/sedes/",                            None,   "Sedes - GET lista",                      "ambulancias"),
        ("POST",   "/api/sedes/",                            {"nombre": "S Bench POST", "direccion": "X", "telefono": "300", "responsable": "A", "activa": True},
                                                                     "Sedes - POST crear",                     "ambulancias"),
        ("GET",    f"/api/sedes/{sid}/",                     None,   "Sedes - GET detalle",                    "ambulancias"),
        ("PUT",    f"/api/sedes/{sid}/",                     {"responsable": "Nuevo"},
                                                                     "Sedes - PUT actualizar",                 "ambulancias"),
        ("GET",    "/api/ambulancias/",                      None,   "Ambulancias - GET lista",                "ambulancias"),
        ("POST",   "/api/ambulancias/",                      {"placa": "B{}", "tipo": "BAT", "sede": sid, "estado": 1},
                                                                     "Ambulancias - POST crear",               "ambulancias"),
        ("GET",    f"/api/ambulancias/{aid}/",               None,   "Ambulancias - GET detalle",              "ambulancias"),
        ("PUT",    f"/api/ambulancias/{aid}/",               {"tipo": "MAT"},
                                                                     "Ambulancias - PUT actualizar",           "ambulancias"),
        ("GET",    "/api/soat/",                             None,   "SOAT - GET lista",                       "ambulancias"),
        ("GET",    "/api/soat/?page=1&page_size=10",         None,   "SOAT - GET lista paginada",              "ambulancias"),
        ("GET",    "/api/soat/?search=Bench",                None,   "SOAT - GET búsqueda",                    "ambulancias"),
        ("GET",    f"/api/soat/{rid}/",                      None,   "SOAT - GET detalle",                     "ambulancias"),
        ("PUT",    f"/api/soat/{rid}/",                      {"nombre_paciente": "Actualizado"},
                                                                     "SOAT - PUT actualizar",                  "ambulancias"),
        ("GET",    f"/api/soat/{rid}/exportar/",             None,   "SOAT - GET exportar TXT",                "ambulancias"),
        # ─── usuarios ────────────────────────────────────────────────────────
        ("GET",    "/user/perfil/",                          None,   "Perfil - GET propio",                    "usuarios"),
        ("GET",    "/user/lista-usuarios/",                  None,   "Lista Usuarios - GET",                   "usuarios"),
        ("GET",    "/user/filtrar-usuarios/",                None,   "Filtrar Usuarios - GET sin filtro",      "usuarios"),
        ("GET",    "/user/filtrar-usuarios/?nombre=Bench",   None,   "Filtrar Usuarios - GET por nombre",      "usuarios"),
        ("GET",    "/user/cargo-Nivel-Regional/",            None,   "Cargo/Nivel/Regional - GET",             "usuarios"),
        ("GET",    "/user/Cargo/",                           None,   "Cargo - GET lista",                      "usuarios"),
        ("POST",   "/user/Cargo/",                           {"nombrecargo": "BenchCargo{}", "estadocargo": 1},
                                                                     "Cargo - POST crear",                     "usuarios"),
        ("PUT",    "/user/Cargo/",                           {"idcargo": cid, "nombrecargo": "BenchCargoUpd"},
                                                                     "Cargo - PUT actualizar",                 "usuarios"),
        ("GET",    "/user/Nivel/",                           None,   "Nivel - GET lista",                      "usuarios"),
        ("POST",   "/user/Nivel/",                           {"nombrenivel": "BenchNivel{}", "estadonivel": 1},
                                                                     "Nivel - POST crear",                     "usuarios"),
        ("PUT",    "/user/Nivel/",                           {"idnivel": nid, "nombrenivel": "BenchNivelUpd"},
                                                                     "Nivel - PUT actualizar",                 "usuarios"),
        ("GET",    "/user/Region/",                          None,   "Region - GET lista",                     "usuarios"),
        ("POST",   "/user/Region/",                          {"nombreregional": "BenchRegion{}", "estadoregional": 1},
                                                                     "Region - POST crear",                    "usuarios"),
        ("PUT",    "/user/Region/",                          {"idregional": regid, "nombreregional": "BenchRegionUpd"},
                                                                     "Region - PUT actualizar",                "usuarios"),
        ("GET",    "/user/reporte-usuarios/",                None,   "Reporte Usuarios - GET Excel",           "usuarios"),
    ]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Setup datos de prueba
    print("Preparando fixtures de benchmark...")
    user = _crear_usuario()
    sede = _crear_sede()
    amb  = _crear_ambulancia(sede)
    soat = _crear_soat(sede, amb, user)
    cargo = _crear_cargo()
    nivel = _crear_nivel()
    regional = _crear_regional()
    Organizacion.objects.get_or_create(nombre="Org Test Benchmark", defaults={"nit": "999-9"})

    client = APIClient()
    client.force_authenticate(user=user)

    escenarios = definir_escenarios(sede, amb, soat, user, cargo, nivel, regional)

    resultados = []
    col_ancho = 45

    print(f"\n{'Endpoint':<{col_ancho}} {'N':>4} {'MIN':>8} {'AVG':>8} {'MED':>8} {'P95':>8} {'MAX':>8} {'STDEV':>8} {'STATUS':>7}")
    print("-" * (col_ancho + 62))

    for metodo, path, data, descripcion, modulo in escenarios:
        stats = medir(client, metodo.lower(), path, data)
        resultados.append({
            "modulo": modulo,
            "endpoint": descripcion,
            "metodo": metodo,
            "path": path,
            "n": stats["n"],
            "min_ms": stats["min"],
            "avg_ms": stats["avg"],
            "median_ms": stats["median"],
            "p95_ms": stats["p95"],
            "max_ms": stats["max"],
            "stdev_ms": stats["stdev"],
            "status": stats["status"],
        })

        label = f"[{metodo}] {descripcion}"[:col_ancho]
        print(
            f"{label:<{col_ancho}} {stats['n']:>4} "
            f"{stats['min']:>8.2f} {stats['avg']:>8.2f} {stats['median']:>8.2f} "
            f"{stats['p95']:>8.2f} {stats['max']:>8.2f} {stats['stdev']:>8.2f} "
            f"{stats['status']:>7}"
        )

    # Exportar CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=resultados[0].keys())
        writer.writeheader()
        writer.writerows(resultados)

    print(f"\nCSV exportado: {OUTPUT_CSV}")

    # Resumen global
    avgs = [r["avg_ms"] for r in resultados]
    print(f"\n── Resumen global ──────────────────────────────")
    print(f"  Endpoints medidos : {len(resultados)}")
    print(f"  Total peticiones  : {len(resultados) * REPETICIONES}")
    print(f"  AVG global        : {round(statistics.mean(avgs), 2)} ms")
    print(f"  Más rápido        : {min(avgs):.2f} ms — {resultados[avgs.index(min(avgs))]['endpoint']}")
    print(f"  Más lento         : {max(avgs):.2f} ms — {resultados[avgs.index(max(avgs))]['endpoint']}")

    return resultados


if __name__ == "__main__":
    main()
