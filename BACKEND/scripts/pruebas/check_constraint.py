import sqlalchemy as sa
from sqlalchemy import create_engine, text

DB_URL = "mysql+mysqldb://root:@localhost/formularios?charset=utf8mb4"
engine = create_engine(DB_URL)

conn = engine.connect()

# Ver estructura de la tabla
result = conn.execute(text("SHOW CREATE TABLE examenes_examenescargo"))
table_structure = result.fetchone()[1]

print("=== ESTRUCTURA ACTUAL ===")
print(table_structure)

conn.close()
