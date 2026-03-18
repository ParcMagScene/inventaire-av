"""
database_migrations.py — Système de migrations SQLite idempotentes.

- Table meta(key, value) pour stocker db_version
- Migrations numérotées appliquées séquentiellement
- Détection automatique de la version courante
- Application automatique au lancement
- Jamais d'écrasement de la base existante
"""
import sqlite3
from typing import List, Tuple, Callable


# ─── Table meta ──────────────────────────────────────────
_META_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
"""


def _ensure_meta(conn: sqlite3.Connection):
    """Crée la table meta si elle n'existe pas."""
    conn.executescript(_META_SCHEMA)


def get_db_version(conn: sqlite3.Connection) -> int:
    """Retourne la version actuelle de la base (0 si aucune migration)."""
    _ensure_meta(conn)
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'db_version'"
    ).fetchone()
    if row:
        try:
            return int(row[0])
        except (ValueError, TypeError):
            return 0
    return 0


def _set_db_version(conn: sqlite3.Connection, version: int):
    """Met à jour la version de la base."""
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('db_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(version),),
    )


# ─── Utilitaire : vérifier si une colonne existe ────────
def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row[0] > 0


# ═════════════════════════════════════════════════════════
#  MIGRATIONS — Chaque fonction prend (conn) et est idempotente
# ═════════════════════════════════════════════════════════

def migration_001(conn: sqlite3.Connection):
    """v1 → Ajout colonne confidence_score + tables outillage."""
    # confidence_score (déjà géré par _migrate_db, mais on le rend idempotent)
    if not _column_exists(conn, "articles", "confidence_score"):
        conn.execute(
            "ALTER TABLE articles ADD COLUMN confidence_score INTEGER DEFAULT 0"
        )

    # Tables catalogue outillage
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tool_categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            icon        TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS tool_types (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id     INTEGER NOT NULL REFERENCES tool_categories(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            default_ref     TEXT DEFAULT '',
            default_price   REAL DEFAULT 0.0,
            UNIQUE(category_id, name)
        );

        CREATE INDEX IF NOT EXISTS idx_tool_types_category
            ON tool_types(category_id);
    """)

    # Lien articles → tool_type_id
    if not _column_exists(conn, "articles", "tool_type_id"):
        conn.execute(
            "ALTER TABLE articles ADD COLUMN tool_type_id INTEGER "
            "REFERENCES tool_types(id) ON DELETE SET NULL"
        )


def migration_002(conn: sqlite3.Connection):
    """v2 → Index de performance sur articles."""
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_articles_category
            ON articles(category_id);
        CREATE INDEX IF NOT EXISTS idx_articles_location
            ON articles(location_id);
        CREATE INDEX IF NOT EXISTS idx_articles_supplier
            ON articles(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_articles_tool_type
            ON articles(tool_type_id);
        CREATE INDEX IF NOT EXISTS idx_history_article
            ON history(article_id);
    """)


# ─── Registre des migrations ─────────────────────────────
# Ordre : (version, fonction)
MIGRATIONS: List[Tuple[int, Callable]] = [
    (1, migration_001),
    (2, migration_002),
]


# ─── Point d'entrée ─────────────────────────────────────
def run_migrations(conn: sqlite3.Connection):
    """Applique toutes les migrations nécessaires (idempotentes)."""
    current = get_db_version(conn)
    applied = 0

    for version, func in MIGRATIONS:
        if version > current:
            try:
                func(conn)
                _set_db_version(conn, version)
                applied += 1
                print(f"  [Migration] v{version} appliquée")
            except Exception as e:
                print(f"  [Migration] ERREUR v{version} : {e}")
                raise

    if applied == 0 and current > 0:
        pass  # Silencieux si tout est à jour
    elif applied > 0:
        print(f"  [Migration] {applied} migration(s) appliquée(s) — version {get_db_version(conn)}")
    else:
        # Première initialisation
        _set_db_version(conn, max(v for v, _ in MIGRATIONS) if MIGRATIONS else 0)
