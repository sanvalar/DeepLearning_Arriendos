import sqlite3

PATH = "vivienda_estudiantil.db"

REPLACEMENTS = {
    "Fincara�z": "Fincaraíz",
    "Itag��": "Itagüí",
    "Medell�n": "Medellín",
    "Bogot�": "Bogotá",
}

connection = sqlite3.connect(PATH)
for column in ("fuente", "titulo", "barrio"):
    rows = connection.execute(f"SELECT id, {column} FROM inmuebles WHERE {column} LIKE '%�%' ").fetchall()
    for record_id, value in rows:
        repaired = value or ""
        for damaged, correct in REPLACEMENTS.items():
            repaired = repaired.replace(damaged, correct)
        connection.execute(f"UPDATE inmuebles SET {column}=? WHERE id=?", (repaired, record_id))
connection.commit()
print(f"Datos actualizados en {PATH}")
connection.close()
