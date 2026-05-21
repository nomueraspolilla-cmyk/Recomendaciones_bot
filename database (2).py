import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "recommendations.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                synopsis TEXT,
                genre TEXT,
                country TEXT,
                year INTEGER,
                director_author TEXT,
                url TEXT,
                added_by TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col, tipo in [
            ("synopsis", "TEXT"), ("genre", "TEXT"), ("country", "TEXT"),
            ("year", "INTEGER"), ("director_author", "TEXT")
        ]:
            try:
                conn.execute(f"ALTER TABLE recommendations ADD COLUMN {col} {tipo}")
            except Exception:
                pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON recommendations(title)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON recommendations(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_genre ON recommendations(genre)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON recommendations(year)")
        conn.commit()


def save_recommendation(title, category, description, url, added_by,
                        synopsis=None, genre=None, country=None, year=None, director_author=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO recommendations
               (title, category, description, synopsis, genre, country, year, director_author, url, added_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, category, description, synopsis, genre, country, year, director_author, url, added_by),
        )
        conn.commit()


def search_recommendations(query: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM recommendations
               WHERE title LIKE ? OR description LIKE ? OR genre LIKE ? OR director_author LIKE ?
               ORDER BY date DESC LIMIT 10""",
            (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
    return [dict(r) for r in rows]


def find_one(title: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE title LIKE ? ORDER BY date DESC LIMIT 1",
            (f"%{title}%",),
        ).fetchone()
    return dict(row) if row else None


def list_by_category(category: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE category = ? ORDER BY date DESC",
            (category,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_by_genre(genre: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE genre LIKE ? ORDER BY date DESC",
            (f"%{genre}%",),
        ).fetchall()
    return [dict(r) for r in rows]


def list_by_year(year: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE year = ? ORDER BY title",
            (year,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_by_country(country: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE country LIKE ? ORDER BY date DESC",
            (f"%{country}%",),
        ).fetchall()
    return [dict(r) for r in rows]
