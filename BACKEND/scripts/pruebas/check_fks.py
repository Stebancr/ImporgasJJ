import sqlalchemy as sa
from sqlalchemy import create_engine, text

DB_URL = "mysql+mysqldb://root:@localhost/formularios?charset=utf8mb4"
engine = create_engine(DB_URL)

conn = engine.connect()

# Ver todas las tablas que referencian examenes_examenescargo
result = conn.execute(text("""
    SELECT 
        TABLE_NAME, 
        CONSTRAINT_NAME, 
        REFERENCED_TABLE_NAME,
        REFERENCED_COLUMN_NAME
    FROM information_schema.KEY_COLUMN_USAGE
    WHERE REFERENCED_TABLE_NAME = 'examenes_examenescargo'
"""))

print("=== FOREIGN KEYS QUE APUNTAN A examenes_examenescargo ===")
for row in result:
    print(f"Tabla: {row[0]}, Constraint: {row[1]}, Referencia: {row[2]}.{row[3]}")

conn.close()
