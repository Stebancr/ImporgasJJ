from sqlalchemy import create_engine, text

DB_URL = "mysql+mysqldb://root:@localhost/formularios?charset=utf8mb4"
engine = create_engine(DB_URL)

conn = engine.connect()
trans = conn.begin()

try:
    # Asegurar índice para la FK de empresa antes de soltar el índice único existente
    print("Agregando índice simple en empresa_id (por si la FK lo necesita)...")
    try:
        conn.execute(text("""
            ALTER TABLE examenes_examenescargo 
            ADD INDEX idx_empresa_id (empresa_id)
        """))
        print("✓ Índice idx_empresa_id creado")
    except Exception as idx_err:
        # Si ya existía, MySQL lanzará error 1061 de índice duplicado; lo ignoramos.
        print(f"(Aviso) No se creó idx_empresa_id: {idx_err}")

    # Eliminar constraint antigua que no incluye tipo
    print("Eliminando constraint antigua sin tipo...")
    conn.execute(text("""
        ALTER TABLE examenes_examenescargo 
        DROP INDEX examenes_examenescargo_empresa_id_cargo_id_exam_9accaab9_uniq
    """))

    # Crear nueva constraint que sí incluye tipo
    print("Creando nueva constraint con tipo...")
    conn.execute(text("""
        ALTER TABLE examenes_examenescargo 
        ADD UNIQUE KEY unique_empresa_cargo_examen_tipo (empresa_id, cargo_id, examen_id, tipo)
    """))

    trans.commit()
    print("\n✓ Constraint actualizada correctamente")

    # Verificar estructura resultante
    result = conn.execute(text("SHOW CREATE TABLE examenes_examenescargo"))
    print("\n=== NUEVA ESTRUCTURA ===")
    print(result.fetchone()[1])

except Exception as e:
    trans.rollback()
    print(f"✗ ERROR: {e}")

conn.close()
