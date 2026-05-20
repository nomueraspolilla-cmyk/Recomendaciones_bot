import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "recomendaciones.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recomendaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                descripcion TEXT,
                url TEXT,
                remitente TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_titulo ON recomendaciones(titulo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_categoria ON recomendaciones(categoria)")
        conn.commit()


def guardar_recomendacion(titulo, categoria, descripcion, url, remitente):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO recomendaciones (titulo, categoria, descripcion, url, remitente) VALUES (?, ?, ?, ?, ?)",
            (titulo, categoria, descripcion, url, remitente),
        )
        conn.commit()


def buscar_recomendaciones(query: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM recomendaciones
               WHERE titulo LIKE ? OR descripcion LIKE ?
               ORDER BY fecha DESC LIMIT 10""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    return [dict(r) for r in rows]


def listar_por_categoria(categoria: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recomendaciones WHERE categoria = ? ORDER BY fecha DESC",
            (categoria,),
        ).fetchall()
    return [dict(r) for r in rows]
