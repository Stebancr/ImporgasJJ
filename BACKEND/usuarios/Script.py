import os
import sys
import django
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from django.contrib.auth.hashers import make_password
from django.db import transaction
import unicodedata

# ========================
# Configurar Django
# ========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
# Configurar logging: archivo en la misma carpeta del script
BASE_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_SCRIPT_DIR, "script_colaboradores.log")

logger = logging.getLogger("usuarios_script")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)

# ahora importar modelos
from usuarios.models import (
    Colaboradores,
    Usuarios,
    Cargo,
    Niveles,
    Regional
)

from analitica.models import Centroop


# ========================
# UTILIDADES
# ========================
def get_valor(fila, *columnas):
    """
    Retorna el primer valor NO vacío encontrado entre varias columnas
    (maneja columnas duplicadas: col, col.1, col.2, etc.)
    """
    for col in columnas:
        valor = fila.get(col)
        if pd.notna(valor) and str(valor).strip() != "":
            return str(valor).strip()
    return None


def separar_nombre_apellido(nombre_completo):
    """
    Reglas actualizadas:
    - 3 palabras → 2 apellidos + 1 nombre
    - 4 palabras → 2 apellidos + 2 nombres
    """
    if not nombre_completo:
        return None, None

    partes = nombre_completo.split()

    if len(partes) < 2:
        return None, None

    if len(partes) == 2:
        # 1 apellido, 1 nombre
        return partes[1], partes[0]

    if len(partes) == 3:
        # 2 apellidos, 1 nombre
        return " ".join(partes[:2]), partes[2]

    if len(partes) == 4:
        # 2 apellidos, 2 nombres
        return " ".join(partes[:2]), " ".join(partes[2:])

    # Más de 4 palabras: 2 apellidos, resto nombres
    return " ".join(partes[:2]), " ".join(partes[2:])


def obtener_email(fila):
    """
    Prioridad:
    1. corporativo
    2. email_del_contacto
    """

    corporativo = None
    for key in ("correo_corporativo", "corporativo", "corporate_email"):
        val = fila.get(key)
        if pd.notna(val):
            val_str = str(val).strip()
            # Considerar como inválido si es '#N/D', '#N/A', 'N/D', 'N/A', '-', vacío o similar
            if val_str and val_str.upper() not in {"#N/D", "#N/A", "N/D", "N/A", "-"}:
                corporativo = val_str
                break

    contacto = None
    for key in ("email_del_contacto", "email", "email_contacto"):
        val = fila.get(key)
        if pd.notna(val) and str(val).strip():
            contacto = str(val).strip()
            break

    # Validar formato simple de email
    def es_email_valido(email):
        import re
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

    if corporativo and es_email_valido(corporativo):
        return corporativo
    if contacto and es_email_valido(contacto):
        return contacto
    # Si corporativo está vacío o no es válido, pero contacto existe, usarlo aunque no sea válido
    if not corporativo and contacto:
        return contacto
    return None


def limpiar_telefono(valor):
    """Sanitiza el teléfono: mantiene dígitos y un posible + inicial. Devuelve None si inválido."""
    if pd.isna(valor) or valor is None:
        return None
    s = str(valor).strip()
    if not s:
        return None
    import re
    # conservar + solo si está al inicio
    s = s.replace(" ", "")
    cleaned = re.sub(r"[^0-9+]", "", s)
    if cleaned.startswith("+"):
        digits = re.sub(r"\D", "", cleaned[1:])
        if len(digits) < 6:
            return None
        return "+" + digits
    else:
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 6:
            return None
        return digits


# ========================
# CARGA PRINCIPAL
# ========================
def cargar_colaboradores_desde_excel():

    # Preferir MACRO2.xlsx si está disponible en templates (por pedido)
    base_templates = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    preferred = os.path.join(base_templates, "macro3.xlsx")
    fallback = os.path.join(base_templates, "Colaboradores.xlsx")

    if os.path.exists(preferred):
        excel_path = preferred
    else:
        excel_path = fallback

    if not os.path.exists(excel_path):
        logger.error(f"No se encontró el archivo: {excel_path}")
        print(f"❌ No se encontró el archivo: {excel_path}")
        return

    # Leer Excel
    df = pd.read_excel(excel_path)
    df = df.iloc[:1466]  # Limita la lectura hasta la fila 1466 (0-indexed, incluye 0-1465)

    # Normalizar columnas
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    logger.info("Columnas detectadas:")
    logger.info(df.columns.tolist())
    logger.info(f"Filas encontradas: {len(df)}")

    # FKs fijas
    regional = Regional.objects.get(idregional=1)

    exitosos = 0
    errores = 0
    log_errores = []
    filas_validas = []

    for index, fila in df.iterrows():
        fila_num = index + 2  # Excel empieza en fila 2
        try:
            cedula = get_valor(fila, "empleado", "empleado.1")
            nombre_completo = get_valor(
                fila,
                "nombre_del_empleado",
                "nombre_del_empleado.1"
            )

            if not cedula or not nombre_completo:
                log_errores.append(f"Fila {fila_num}: Empleado o Nombre vacío")
                errores += 1
                continue

            nombre, apellido = separar_nombre_apellido(nombre_completo)

            if not nombre or not apellido:
                log_errores.append(f"Fila {fila_num}: Nombre inválido ({nombre_completo})")
                errores += 1
                continue

            email = obtener_email(fila)

            # Obtener y sanitizar teléfono
            telefono_val = get_valor(fila, "telefono_del_contacto", "telefono_del_contacto.1", "telefono_del_contacto.2")
            telefono = limpiar_telefono(telefono_val)

            if not email:
                log_errores.append(f"Fila {fila_num}: Sin email válido (ni corporativo ni contacto)")
                errores += 1
                continue

            usuario = cedula


            # Buscar nivel por nombre similar (ignorando tildes, mayúsculas y permitiendo coincidencia parcial)
            nombre_nivel = get_valor(fila, "jerarquia")
            def normalizar(texto):
                if not texto:
                    return ""
                return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii').strip().lower()

            nombre_nivel_norm = normalizar(nombre_nivel)
            niveles_db = list(Niveles.objects.all())
            nivel = None
            for n in niveles_db:
                n_norm = normalizar(n.nombrenivel)
                if nombre_nivel_norm == n_norm or nombre_nivel_norm in n_norm or n_norm in nombre_nivel_norm:
                    nivel = n
                    break
            if not nivel:
                log_errores.append(f"Fila {fila_num}: Nivel '{nombre_nivel}' no encontrado (normalizado: '{nombre_nivel_norm}')")
                errores += 1
                continue

            # Buscar cargo por nombre exacto
            nombre_cargo = get_valor(fila, "desc_cargo")
            cargo = Cargo.objects.filter(nombrecargo__iexact=nombre_cargo).first()
            if not cargo:
                log_errores.append(f"Fila {fila_num}: Cargo '{nombre_cargo}' no encontrado")
                errores += 1
                continue

            # Ahora la columna 'Centro de Operacion' contiene el ID del Centroop
            # Se espera un número (o string numérico). Si no existe, marcar error.
            centro_id_val = get_valor(fila, "centro_de_operacion")
            centro_id = None
            if centro_id_val is not None:
                try:
                    centro_id = int(float(centro_id_val))
                except Exception:
                    centro_id = None

            if centro_id is None:
                log_errores.append(f"Fila {fila_num}: Centro de Operacion vacío o inválido ('{centro_id_val}')")
                errores += 1
                continue

            from analitica.models import Centroop
            centro_op = Centroop.objects.filter(idcentrop=centro_id).first()
            if not centro_op:
                log_errores.append(f"Fila {fila_num}: Centro de operación con id '{centro_id}' no encontrado")
                errores += 1
                continue

            if Colaboradores.objects.filter(cccolaborador=usuario).exists():
                log_errores.append(f"Fila {fila_num}: CC {usuario} ya existe")
                errores += 1
                continue

            # Si todo está bien, guardar la fila para procesar después
            # Truncar email a 50 caracteres para evitar error de longitud
            email_trunc = email[:50] if email else None
            filas_validas.append({
                "usuario": usuario,
                "nombre": nombre,
                "apellido": apellido,
                "cargo": cargo,
                "email": email_trunc,
                "nivel": nivel,
                "telefono": telefono,
                "regional": regional,
                "centro_op": centro_op
            })
        except Exception as e:
            log_errores.append(f"Fila {fila_num}: {e}")
            errores += 1

    logger.info("\n==============================")
    logger.info("Comprobando errores antes de insertar datos...")
    if log_errores:
        logger.error("Se detectaron errores en el archivo de entrada. No se realizará ninguna inserción.")
        for err in log_errores:
            logger.error(err)
        # Indicar al usuario dónde revisar el log
        print(f"\n❌ No se cargaron datos por errores detectados. Revisa el log en: {LOG_FILE}\n")
        return

    logger.info("No se detectaron errores. Procediendo a cargar datos...")

    try:
        with transaction.atomic():
            for fila in filas_validas:
                colaborador = Colaboradores.objects.create(
                    cccolaborador=fila["usuario"],
                    nombrecolaborador=fila["nombre"],
                    apellidocolaborador=fila["apellido"],
                    cargocolaborador=fila["cargo"],
                    correocolaborador=fila["email"],
                    telefocolaborador=fila.get("telefono"),
                    estadocolaborador=1,
                    nivelcolaborador=fila["nivel"],
                    regionalcolab=fila["regional"],
                    centroop=fila["centro_op"]
                )

                Usuarios.objects.create(
                    usuario=fila["usuario"],
                    password=make_password(fila["usuario"]),
                    tipousuario=3,
                    idcolaboradoru=colaborador
                )

                logger.info(f"✅ {fila['nombre']} {fila['apellido']} | CC {fila['usuario']}")
                exitosos += 1
    except Exception as e:
        logger.exception("Error al guardar lote; ninguna fila fue insertada: %s", e)
        errores = len(filas_validas)

    logger.info("\n==============================")
    logger.info("RESUMEN FINAL")
    logger.info(f"Exitosos: {exitosos}")
    logger.info(f"Errores: {errores}")
    logger.info("==============================\n")


# ========================
# EJECUCIÓN
# ========================
if __name__ == "__main__":
    logger.info("🚀 Iniciando carga de colaboradores...")
    cargar_colaboradores_desde_excel()
    logger.info("✨ Proceso finalizado")
