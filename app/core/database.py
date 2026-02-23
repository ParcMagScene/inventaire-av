"""
database.py — Couche d'accès SQLite : création du schéma, CRUD, seed.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from .models import (
    Article, Category, Location, Supplier,
    PriceRule, CategoryPriceMode, ReferencePriceMode, PriceHistory,
)

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_db_path() -> Path:
    """Résout le chemin de la base selon le mode (installé / portable / USB)."""
    # 1) Variable d'environnement forcée
    env_path = os.environ.get("INVENTAIRE_DB_PATH")
    if env_path:
        return Path(env_path)
    # 2) Chemin relatif standard
    return BASE_DIR / "data" / "inventaire.db"


DB_PATH = _resolve_db_path()


def _settings() -> dict:
    path = BASE_DIR / "config" / "settings.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ─── Connexion ────────────────────────────────────────────
@contextmanager
def get_connection(db_path: str | Path | None = None):
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Schéma ──────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    DEFAULT '',
    default_price REAL  DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS suppliers (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE,
    contact  TEXT DEFAULT '',
    email    TEXT DEFAULT '',
    phone    TEXT DEFAULT '',
    profile  TEXT DEFAULT 'moyen',
    notes    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reference       TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    category_id     INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    location_id     INTEGER REFERENCES locations(id)  ON DELETE SET NULL,
    supplier_id     INTEGER REFERENCES suppliers(id)  ON DELETE SET NULL,
    quantity        INTEGER DEFAULT 0,
    quantity_min    INTEGER DEFAULT 0,
    price_mode      TEXT    DEFAULT 'automatique',
    price_avg       REAL    DEFAULT 0.0,
    price_low       REAL    DEFAULT 0.0,
    price_high      REAL    DEFAULT 0.0,
    price_manual    REAL,
    price_manual_low  REAL,
    price_manual_high REAL,
    confidence      TEXT    DEFAULT 'faible',
    price_source    TEXT    DEFAULT '',
    notes           TEXT    DEFAULT '',
    created_at      TEXT    DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS price_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT    NOT NULL UNIQUE,
    value       REAL    DEFAULT 0.0,
    description TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS category_price_modes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    price_mode  TEXT    DEFAULT 'automatique'
);

CREATE TABLE IF NOT EXISTS reference_price_modes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reference   TEXT    NOT NULL UNIQUE,
    price_mode  TEXT    DEFAULT 'automatique',
    fixed_price REAL    DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    price       REAL    NOT NULL,
    quantity    INTEGER DEFAULT 1,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    date        TEXT    DEFAULT (datetime('now','localtime')),
    notes       TEXT    DEFAULT ''
);
"""


def init_db(db_path: str | Path | None = None):
    """Crée les tables si elles n'existent pas et injecte les données par défaut."""
    os.makedirs(os.path.dirname(str(db_path or DB_PATH)), exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(_SCHEMA)
        _migrate_db(conn)
        _seed_defaults(conn)


def _migrate_db(conn: sqlite3.Connection):
    """Migrations sûres — ajout de colonnes sans perte de données existantes."""
    cursor = conn.execute("PRAGMA table_info(articles)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if "confidence_score" not in existing_cols:
        conn.execute("ALTER TABLE articles ADD COLUMN confidence_score INTEGER DEFAULT 0")


def _seed_defaults(conn: sqlite3.Connection):
    """Charge les catégories, emplacements et règles par défaut si les tables sont vides."""
    defaults_dir = BASE_DIR / "config" / "defaults"

    # Catégories
    if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        path = defaults_dir / "default_categories.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for c in json.load(f):
                    conn.execute(
                        "INSERT INTO categories (name, description, default_price) VALUES (?,?,?)",
                        (c["name"], c.get("description", ""), c.get("default_price", 0.0)),
                    )

    # Emplacements
    if conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0] == 0:
        path = defaults_dir / "default_locations.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for loc in json.load(f):
                    conn.execute(
                        "INSERT INTO locations (name, description) VALUES (?,?)",
                        (loc["name"], loc.get("description", "")),
                    )

    # Règles de prix
    if conn.execute("SELECT COUNT(*) FROM price_rules").fetchone()[0] == 0:
        path = defaults_dir / "default_price_rules.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                rules = json.load(f)
                for key in ("price_low_factor", "price_high_factor", "outlier_sigma",
                            "history_decay_days", "min_history_entries"):
                    if key in rules:
                        conn.execute(
                            "INSERT INTO price_rules (key, value, description) VALUES (?,?,?)",
                            (key, float(rules[key]), key),
                        )
                # Source weights
                for k, v in rules.get("source_weights", {}).items():
                    conn.execute(
                        "INSERT INTO price_rules (key, value, description) VALUES (?,?,?)",
                        (f"weight_{k}", float(v), f"Poids source {k}"),
                    )
                # Supplier profiles
                for k, v in rules.get("supplier_profiles", {}).items():
                    conn.execute(
                        "INSERT INTO price_rules (key, value, description) VALUES (?,?,?)",
                        (f"supplier_{k}", float(v), f"Profil fournisseur {k}"),
                    )


# ─── CRUD Catégories ──────────────────────────────────────
def get_categories(db_path=None) -> List[Category]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
        return [Category(**dict(r)) for r in rows]


def add_category(cat: Category, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO categories (name, description, default_price) VALUES (?,?,?)",
            (cat.name, cat.description, cat.default_price),
        )
        return cur.lastrowid


def update_category(cat: Category, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE categories SET name=?, description=?, default_price=? WHERE id=?",
            (cat.name, cat.description, cat.default_price, cat.id),
        )


def delete_category(cat_id: int, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))


# ─── CRUD Emplacements ───────────────────────────────────
def get_locations(db_path=None) -> List[Location]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM locations ORDER BY name").fetchall()
        return [Location(**dict(r)) for r in rows]


def add_location(loc: Location, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO locations (name, description) VALUES (?,?)",
            (loc.name, loc.description),
        )
        return cur.lastrowid


def update_location(loc: Location, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE locations SET name=?, description=? WHERE id=?",
            (loc.name, loc.description, loc.id),
        )


def delete_location(loc_id: int, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM locations WHERE id=?", (loc_id,))


# ─── CRUD Fournisseurs ───────────────────────────────────
def get_suppliers(db_path=None) -> List[Supplier]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
        return [Supplier(**dict(r)) for r in rows]


def add_supplier(s: Supplier, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO suppliers (name, contact, email, phone, profile, notes) VALUES (?,?,?,?,?,?)",
            (s.name, s.contact, s.email, s.phone, s.profile, s.notes),
        )
        return cur.lastrowid


def update_supplier(s: Supplier, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE suppliers SET name=?, contact=?, email=?, phone=?, profile=?, notes=? WHERE id=?",
            (s.name, s.contact, s.email, s.phone, s.profile, s.notes, s.id),
        )


def delete_supplier(s_id: int, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM suppliers WHERE id=?", (s_id,))


# ─── CRUD Articles ─────────────────────────────────────
def get_articles(db_path=None, category_id: int | None = None,
                 location_id: int | None = None,
                 search: str = "") -> List[Article]:
    sql = """
        SELECT a.*,
               COALESCE(c.name,'') AS category_name,
               COALESCE(l.name,'') AS location_name,
               COALESCE(s.name,'') AS supplier_name
        FROM articles a
        LEFT JOIN categories c ON a.category_id = c.id
        LEFT JOIN locations  l ON a.location_id = l.id
        LEFT JOIN suppliers  s ON a.supplier_id = s.id
        WHERE 1=1
    """
    params: list = []
    if category_id:
        sql += " AND a.category_id = ?"
        params.append(category_id)
    if location_id:
        sql += " AND a.location_id = ?"
        params.append(location_id)
    if search:
        sql += " AND (a.name LIKE ? OR a.reference LIKE ? OR a.description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += " ORDER BY a.name"
    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        articles = []
        for r in rows:
            d = dict(r)
            articles.append(Article(**d))
        return articles


def add_article(a: Article, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute("""
            INSERT INTO articles
                (reference, name, description, category_id, location_id, supplier_id,
                 quantity, quantity_min, price_mode,
                 price_avg, price_low, price_high,
                 price_manual, price_manual_low, price_manual_high,
                 confidence, confidence_score, price_source, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            a.reference, a.name, a.description, a.category_id,
            a.location_id, a.supplier_id, a.quantity, a.quantity_min,
            a.price_mode, a.price_avg, a.price_low, a.price_high,
            a.price_manual, a.price_manual_low, a.price_manual_high,
            a.confidence, a.confidence_score, a.price_source, a.notes,
        ))
        return cur.lastrowid


def update_article(a: Article, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("""
            UPDATE articles SET
                reference=?, name=?, description=?, category_id=?, location_id=?,
                supplier_id=?, quantity=?, quantity_min=?, price_mode=?,
                price_avg=?, price_low=?, price_high=?,
                price_manual=?, price_manual_low=?, price_manual_high=?,
                confidence=?, confidence_score=?, price_source=?, notes=?,
                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (
            a.reference, a.name, a.description, a.category_id,
            a.location_id, a.supplier_id, a.quantity, a.quantity_min,
            a.price_mode, a.price_avg, a.price_low, a.price_high,
            a.price_manual, a.price_manual_low, a.price_manual_high,
            a.confidence, a.confidence_score, a.price_source, a.notes, a.id,
        ))


def delete_article(art_id: int, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM articles WHERE id=?", (art_id,))


# ─── Historique des prix ──────────────────────────────────
def get_price_history(article_id: int, db_path=None) -> List[PriceHistory]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM history WHERE article_id=? ORDER BY date DESC", (article_id,)
        ).fetchall()
        return [PriceHistory(**dict(r)) for r in rows]


def add_price_history(h: PriceHistory, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO history (article_id, price, quantity, supplier_id, date, notes) VALUES (?,?,?,?,?,?)",
            (h.article_id, h.price, h.quantity, h.supplier_id, h.date, h.notes),
        )
        return cur.lastrowid


# ─── Règles de prix ──────────────────────────────────────
def get_price_rules(db_path=None) -> dict:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM price_rules").fetchall()
        return {r["key"]: r["value"] for r in rows}


def set_price_rule(key: str, value: float, desc: str = "", db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO price_rules (key, value, description) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, description=excluded.description",
            (key, value, desc),
        )


# ─── Catégorie price modes ────────────────────────────────
def get_category_price_modes(db_path=None) -> List[CategoryPriceMode]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM category_price_modes").fetchall()
        return [CategoryPriceMode(**dict(r)) for r in rows]


def set_category_price_mode(category_id: int, mode: str, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO category_price_modes (category_id, price_mode) VALUES (?,?) "
            "ON CONFLICT(category_id) DO UPDATE SET price_mode=excluded.price_mode",
            (category_id, mode),
        )


# ─── Reference price modes ───────────────────────────────
def get_reference_price_modes(db_path=None) -> List[ReferencePriceMode]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM reference_price_modes").fetchall()
        return [ReferencePriceMode(**dict(r)) for r in rows]


def set_reference_price_mode(ref: str, mode: str, fixed: float = 0.0, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO reference_price_modes (reference, price_mode, fixed_price) VALUES (?,?,?) "
            "ON CONFLICT(reference) DO UPDATE SET price_mode=excluded.price_mode, fixed_price=excluded.fixed_price",
            (ref, mode, fixed),
        )


# ─── Statistiques ────────────────────────────────────────
def get_stats(db_path=None) -> dict:
    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        total_qty = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM articles").fetchone()[0]
        total_value = conn.execute(
            "SELECT COALESCE(SUM(quantity * price_avg),0) FROM articles"
        ).fetchone()[0]
        total_value_low = conn.execute(
            "SELECT COALESCE(SUM(quantity * price_low),0) FROM articles"
        ).fetchone()[0]
        total_value_high = conn.execute(
            "SELECT COALESCE(SUM(quantity * price_high),0) FROM articles"
        ).fetchone()[0]
        low_stock = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE quantity <= quantity_min AND quantity_min > 0"
        ).fetchone()[0]
        inconsistent = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE price_low > price_avg OR price_avg > price_high"
        ).fetchone()[0]
        return {
            "total_articles": total,
            "total_quantity": total_qty,
            "total_value": round(total_value, 2),
            "total_value_low": round(total_value_low, 2),
            "total_value_high": round(total_value_high, 2),
            "low_stock_count": low_stock,
            "inconsistent_count": inconsistent,
        }


def get_recent_updates(db_path=None, limit: int = 10) -> list:
    """Retourne les N derniers articles mis à jour."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT a.reference, a.name, a.price_avg, a.updated_at "
            "FROM articles a ORDER BY a.updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
