from datetime import datetime
from sqlalchemy import create_engine, text

DB_URL = "mysql+mysqldb://root:@localhost/formularios?charset=utf8mb4"
engine = create_engine(DB_URL)

INICIO = "2026-01-04 14:57:47"
FIN = "2026-01-04 14:57:49"
EMPRESA = 7

with engine.begin() as conn:
    count_before = conn.execute(
        text(
            "SELECT COUNT(*) FROM examenes_examenescargo WHERE empresa_id=:emp AND fecha_creacion BETWEEN :a AND :b"
        ),
        {"emp": EMPRESA, "a": INICIO, "b": FIN},
    ).scalar_one()

    deleted = conn.execute(
        text(
            "DELETE FROM examenes_examenescargo WHERE empresa_id=:emp AND fecha_creacion BETWEEN :a AND :b"
        ),
        {"emp": EMPRESA, "a": INICIO, "b": FIN},
    ).rowcount

    count_after = conn.execute(
        text(
            "SELECT COUNT(*) FROM examenes_examenescargo WHERE empresa_id=:emp AND fecha_creacion BETWEEN :a AND :b"
        ),
        {"emp": EMPRESA, "a": INICIO, "b": FIN},
    ).scalar_one()

print(f"Registros en ventana antes: {count_before}")
print(f"Eliminados: {deleted}")
print(f"Registros en ventana despues: {count_after}")
