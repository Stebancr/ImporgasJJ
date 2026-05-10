import pandas as pd
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import unicodedata
import re
import sys
import argparse

# ===============================
# SCRIPT DE IMPORTACION DE EXAMENES
# ===============================
# 
# Este script lee un archivo Excel con la matriz de exámenes por cargo
# y los inserta en la tabla examenes_examenescargo.
#
# CONFIGURACION IMPORTANTE:
# - TIPO_EXAMEN: Define el tipo de exámenes: "INGRESO", "PERIODICO" o "RETIRO"
# - EMPRESA_ID: ID de la empresa en la base de datos
# - EXCEL_PATH: Ruta del archivo Excel a procesar
#
# FORMATO DEL EXCEL:
# - Primera columna: Nombres de los cargos
# - Columnas siguientes: Nombres de exámenes
# - Celdas con 'I', 'P', 'R', 'X' o similar indican que el examen aplica
#
# NOTA: Todos los registros existentes con el mismo tipo no se duplican
# ===============================

# ===============================
# CONFIGURACION
# ===============================

EXCEL_PATH = "Libro1.xlsx"
EMPRESA_ID = 8
LOG_FILE = "import_examenes.log"
RETIRO_DEFAULT_EXAM_NAME = "EXAMEN MEDICO OCUPACIONAL"

DB_URL = "mysql+mysqldb://root:@localhost/formularios?charset=utf8mb4"

# Inicializar engine con fallback a PyMySQL si mysqldb no está disponible
def _create_engine(db_url: str):
    try:
        return create_engine(db_url)
    except Exception as e:
        logging.warning(f"Fallo creando engine con mysqldb: {e}. Probando pymysql...")
        alt_url = db_url.replace("mysql+mysqldb", "mysql+pymysql")
        return create_engine(alt_url)

engine = _create_engine(DB_URL)

# ===============================
# LOGGING
# ===============================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("===== INICIO IMPORTACION EXAMENES =====")

# ===============================
# FUNCIONES
# ===============================

def quitar_tildes(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).upper().strip()
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto)
    texto = unicodedata.normalize("NFKD", texto)
    return texto.encode("ascii", "ignore").decode("ascii")


ALLOWED_TIPOS = {"INGRESO", "PERIODICO", "RETIRO"}

def obtener_tipos_examen(valor):
    """Devuelve lista de tipos aplicables segun el contenido de la celda.
    No interpreta 'X' aquí; se maneja fuera como tipo por defecto.
    """
    if pd.isna(valor):
        return []

    valor_str = str(valor).upper().strip()

    if not valor_str:
        return []

    tipos = []
    # Soportar abreviaturas y palabras completas
    if "INGRESO" in valor_str or re.search(r"\bI\b", valor_str):
        tipos.append("INGRESO")
    if "PERIODICO" in valor_str or re.search(r"\bP\b", valor_str):
        tipos.append("PERIODICO")

    return tipos
def run_import(excel_path: str, empresa_id: int, tipo_por_defecto: str = "INGRESO"):
    # Validar tipo por defecto
    if tipo_por_defecto not in ALLOWED_TIPOS:
        logging.critical(f"Tipo por defecto inválido: {tipo_por_defecto}. Debe ser uno de {sorted(ALLOWED_TIPOS)}")
        sys.exit(1)
    # ===============================
    # CARGA BASE DE DATOS
    # ===============================

    df_cargos = pd.read_sql("SELECT idcargo, nombrecargo FROM cargo", engine)
    df_examenes = pd.read_sql("SELECT id, nombre FROM examenes", engine)

    # Cargar TODAS las relaciones existentes (sin filtrar por tipo aún)
    df_relaciones = pd.read_sql(
        """
        SELECT cargo_id, empresa_id, examen_id, tipo
        FROM examenes_examenescargo
        WHERE empresa_id = %s
        """,
        engine,
        params=(empresa_id,)
    )

    df_cargos["nombre_norm"] = df_cargos["nombrecargo"].apply(quitar_tildes)
    df_examenes["nombre_norm"] = df_examenes["nombre"].apply(quitar_tildes)

    # Resolver examen por defecto para RETIRO
    retiro_nombre_norm = quitar_tildes(RETIRO_DEFAULT_EXAM_NAME)
    retiro_match = df_examenes[df_examenes["nombre_norm"] == retiro_nombre_norm]
    if retiro_match.empty:
        logging.critical(f"No se encontró el examen por defecto de RETIRO: '{RETIRO_DEFAULT_EXAM_NAME}'")
        sys.exit(1)
    retiro_examen_id = int(retiro_match.iloc[0]["id"])

    # ===============================
    # LEER EXCEL
    # ===============================

    df_excel = pd.read_excel(excel_path)
    df_excel.columns = [quitar_tildes(c) for c in df_excel.columns]

    if df_excel.shape[1] < 2:
        logging.critical("El Excel debe tener al menos 2 columnas: Cargo y Exámenes")
        sys.exit(1)

    columna_cargo = df_excel.columns[0]
    columnas_examenes = df_excel.columns[1:]

    # ===============================
    # FASE 1 - VALIDACION Y PREPARACION
    # ===============================

    errores = []
    registros_a_insertar = []

    for idx, row in df_excel.iterrows():

        raw_cargo = row[columna_cargo]
        cargo_excel = quitar_tildes(raw_cargo)
        cargo_match = df_cargos[df_cargos["nombre_norm"] == cargo_excel]

        if not cargo_excel:
            msg = f"CARGO VACIO en fila {idx + 2} (sin nombre tras normalizar)"
            logging.error(msg)
            errores.append(msg)
            continue

        if cargo_match.empty:
            msg = f"CARGO NO ENCONTRADO fila {idx + 2}: '{raw_cargo}' -> '{cargo_excel}'"
            logging.error(msg)
            errores.append(msg)
            continue

        cargo_id = int(cargo_match.iloc[0]["idcargo"])

        for examen_col in columnas_examenes:

            # Obtener los tipos de examen que aplican para esta celda
            cell_val = row[examen_col]
            tipos_aplicables = obtener_tipos_examen(cell_val)

            # Si no hay tipos explícitos, interpretar 'X'/'SI'/TRUE/1 como tipo por defecto
            if not tipos_aplicables:
                val_upper = str(cell_val).strip().upper()
                if val_upper in {"X", "SI", "S", "TRUE", "1", "Y", "YES"}:
                    tipos_aplicables = [tipo_por_defecto]
                else:
                    # Vacío o NO: no aplica
                    continue

            examen_excel = quitar_tildes(examen_col)
            examen_match = df_examenes[df_examenes["nombre_norm"] == examen_excel]

            if examen_match.empty:
                msg = f"EXAMEN NO ENCONTRADO: {examen_excel}"
                logging.error(msg)
                errores.append(msg)
                continue

            examen_id = int(examen_match.iloc[0]["id"])

            # Crear un registro por cada tipo de examen que aplique
            for tipo in tipos_aplicables:

                # Verificar si ya existe esta combinación específica
                existe = df_relaciones[
                    (df_relaciones["cargo_id"] == cargo_id) &
                    (df_relaciones["empresa_id"] == empresa_id) &
                    (df_relaciones["examen_id"] == examen_id) &
                    (df_relaciones["tipo"] == tipo)
                ]

                if not existe.empty:
                    logging.info(f"YA EXISTE: Cargo:{cargo_excel} Examen:{examen_excel} Tipo:{tipo}")
                    continue

                registros_a_insertar.append({
                    "fecha": datetime.now(),
                    "cargo": cargo_id,
                    "empresa": empresa_id,
                    "examen": examen_id,
                    "tipo": tipo,
                    "cargo_nombre": cargo_excel,
                    "examen_nombre": examen_excel
                })

        # Agregar automáticamente configuración de RETIRO con examen por defecto
        existe_retiro = df_relaciones[
            (df_relaciones["cargo_id"] == cargo_id) &
            (df_relaciones["empresa_id"] == empresa_id) &
            (df_relaciones["examen_id"] == retiro_examen_id) &
            (df_relaciones["tipo"] == "RETIRO")
        ]
        if existe_retiro.empty:
            registros_a_insertar.append({
                "fecha": datetime.now(),
                "cargo": cargo_id,
                "empresa": empresa_id,
                "examen": retiro_examen_id,
                "tipo": "RETIRO",
                "cargo_nombre": cargo_excel,
                "examen_nombre": RETIRO_DEFAULT_EXAM_NAME
            })
            logging.info(f"RETIRO AGREGADO: Cargo:{cargo_excel} -> {RETIRO_DEFAULT_EXAM_NAME}")
        else:
            logging.info(f"RETIRO YA EXISTE: Cargo:{cargo_excel}")

    # ===============================
    # DECISION
    # ===============================

    if errores:
        logging.critical("SE ENCONTRARON ERRORES - NO SE INSERTA NADA")
        logging.critical(f"TOTAL ERRORES: {len(errores)}")
        sys.exit(1)

    if not registros_a_insertar:
        logging.info("NO HAY REGISTROS NUEVOS PARA INSERTAR")
        sys.exit(0)

    # ===============================
    # FASE 2 - INSERTAR
    # ===============================

    conn = engine.connect()
    trans = conn.begin()

    try:
        for r in registros_a_insertar:
            conn.execute(
                text("""
                    INSERT INTO examenes_examenescargo
                    (fecha_creacion, cargo_id, empresa_id, examen_id, tipo)
                    VALUES (:fecha, :cargo, :empresa, :examen, :tipo)
                """),
                {
                    "fecha": r["fecha"],
                    "cargo": r["cargo"],
                    "empresa": r["empresa"],
                    "examen": r["examen"],
                    "tipo": r["tipo"]
                }
            )

            logging.info(
                f"ASIGNADO Empresa:{empresa_id} | Cargo:{r['cargo_nombre']} | Examen:{r['examen_nombre']} | Tipo:{r['tipo']}"
            )

        trans.commit()
        logging.info(f"IMPORTACION FINALIZADA CORRECTAMENTE - Total nuevos: {len(registros_a_insertar)}")

    except Exception as e:
        trans.rollback()
        logging.critical("ERROR DURANTE INSERT - ROLLBACK")
        logging.critical(str(e))

    finally:
        conn.close()

    logging.info("===== FIN IMPORTACION EXAMENES =====")

# Ejecución por CLI opcional: permite pasar ruta y empresa
def main():
    parser = argparse.ArgumentParser(description="Importar exámenes por cargo desde Excel")
    parser.add_argument("--excel", dest="excel_path", default=EXCEL_PATH, help="Ruta del archivo Excel")
    parser.add_argument("--empresa", dest="empresa_id", type=int, default=EMPRESA_ID, help="ID de la empresa")
    parser.add_argument("--tipo", dest="tipo", choices=sorted(ALLOWED_TIPOS), default="INGRESO", help="Tipo por defecto para celdas marcadas con 'X'/'SI' (INGRESO, PERIODICO, RETIRO)")
    args = parser.parse_args()

    run_import(args.excel_path, args.empresa_id, args.tipo)

if __name__ == "__main__":
    main()
