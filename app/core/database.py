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
    ToolCategory, ToolType,
)
from .database_migrations import run_migrations

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
        run_migrations(conn)
        _seed_defaults(conn)
        _seed_tool_catalog(conn)


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
                 confidence, confidence_score, price_source, notes, tool_type_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            a.reference, a.name, a.description, a.category_id,
            a.location_id, a.supplier_id, a.quantity, a.quantity_min,
            a.price_mode, a.price_avg, a.price_low, a.price_high,
            a.price_manual, a.price_manual_low, a.price_manual_high,
            a.confidence, a.confidence_score, a.price_source, a.notes,
            getattr(a, 'tool_type_id', None),
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
                tool_type_id=?,
                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (
            a.reference, a.name, a.description, a.category_id,
            a.location_id, a.supplier_id, a.quantity, a.quantity_min,
            a.price_mode, a.price_avg, a.price_low, a.price_high,
            a.price_manual, a.price_manual_low, a.price_manual_high,
            a.confidence, a.confidence_score, a.price_source, a.notes,
            getattr(a, 'tool_type_id', None), a.id,
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


# ═══════════════════════════════════════════════════════════
#  Catalogue Outillage — CRUD
# ═══════════════════════════════════════════════════════════

def get_tool_categories(db_path=None) -> List[ToolCategory]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM tool_categories ORDER BY name").fetchall()
        return [ToolCategory(**dict(r)) for r in rows]


def get_tool_types(db_path=None, category_id: int | None = None) -> List[ToolType]:
    with get_connection(db_path) as conn:
        if category_id:
            rows = conn.execute(
                "SELECT * FROM tool_types WHERE category_id=? ORDER BY name",
                (category_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tool_types ORDER BY name").fetchall()
        return [ToolType(**dict(r)) for r in rows]


def add_tool_category(tc: ToolCategory, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO tool_categories (name, description, icon) VALUES (?,?,?)",
            (tc.name, tc.description, tc.icon),
        )
        return cur.lastrowid


def add_tool_type(tt: ToolType, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO tool_types (category_id, name, description, default_ref, default_price) "
            "VALUES (?,?,?,?,?)",
            (tt.category_id, tt.name, tt.description, tt.default_ref, tt.default_price),
        )
        return cur.lastrowid


# ═══════════════════════════════════════════════════════════
#  Seed — Catalogue outillage pré-rempli
# ═══════════════════════════════════════════════════════════

_TOOL_CATALOG = {
    "Outillage à main": {
        "description": "Outils manuels classiques",
        "icon": "wrench",
        "types": [
            # ── Tournevis plats ──
            ("Tournevis plat 3mm", "Lame plate 3×75mm", 4.0),
            ("Tournevis plat 4mm", "Lame plate 4×100mm", 4.5),
            ("Tournevis plat 5.5mm", "Lame plate 5.5×125mm", 5.0),
            ("Tournevis plat 6.5mm", "Lame plate 6.5×150mm", 5.5),
            ("Tournevis plat 8mm", "Lame plate 8×175mm", 6.0),
            # ── Tournevis cruciformes Phillips ──
            ("Tournevis Phillips PH0", "Cruciforme PH0 – petite vis", 5.0),
            ("Tournevis Phillips PH1", "Cruciforme PH1 – vis moyenne", 5.0),
            ("Tournevis Phillips PH2", "Cruciforme PH2 – vis standard", 5.0),
            ("Tournevis Phillips PH3", "Cruciforme PH3 – grosse vis", 6.0),
            # ── Tournevis cruciformes Pozidriv ──
            ("Tournevis Pozidriv PZ0", "Pozidriv PZ0", 5.0),
            ("Tournevis Pozidriv PZ1", "Pozidriv PZ1", 5.0),
            ("Tournevis Pozidriv PZ2", "Pozidriv PZ2 – le plus courant", 5.0),
            ("Tournevis Pozidriv PZ3", "Pozidriv PZ3", 6.0),
            # ── Tournevis Torx ──
            ("Tournevis Torx T10", "Étoile T10", 6.0),
            ("Tournevis Torx T15", "Étoile T15", 6.0),
            ("Tournevis Torx T20", "Étoile T20", 6.5),
            ("Tournevis Torx T25", "Étoile T25", 6.5),
            ("Tournevis Torx T27", "Étoile T27", 7.0),
            ("Tournevis Torx T30", "Étoile T30", 7.0),
            ("Tournevis Torx T40", "Étoile T40", 7.5),
            # ── Clés Allen (hexagonales) ──
            ("Clé Allen 1.5mm", "Clé hexagonale 1.5mm", 1.5),
            ("Clé Allen 2mm", "Clé hexagonale 2mm", 1.5),
            ("Clé Allen 2.5mm", "Clé hexagonale 2.5mm", 2.0),
            ("Clé Allen 3mm", "Clé hexagonale 3mm", 2.0),
            ("Clé Allen 4mm", "Clé hexagonale 4mm", 2.5),
            ("Clé Allen 5mm", "Clé hexagonale 5mm", 2.5),
            ("Clé Allen 6mm", "Clé hexagonale 6mm", 3.0),
            ("Clé Allen 8mm", "Clé hexagonale 8mm", 3.5),
            ("Clé Allen 10mm", "Clé hexagonale 10mm", 4.0),
            ("Jeu de clés Allen", "Jeu complet 1.5–10mm", 12.0),
            # ── Clés plates ──
            ("Clé plate 6mm", "Clé plate fourche 6mm", 3.0),
            ("Clé plate 7mm", "Clé plate fourche 7mm", 3.0),
            ("Clé plate 8mm", "Clé plate fourche 8mm", 3.5),
            ("Clé plate 10mm", "Clé plate fourche 10mm", 3.5),
            ("Clé plate 11mm", "Clé plate fourche 11mm", 4.0),
            ("Clé plate 12mm", "Clé plate fourche 12mm", 4.0),
            ("Clé plate 13mm", "Clé plate fourche 13mm", 4.5),
            ("Clé plate 14mm", "Clé plate fourche 14mm", 4.5),
            ("Clé plate 17mm", "Clé plate fourche 17mm", 5.0),
            ("Clé plate 19mm", "Clé plate fourche 19mm", 5.5),
            ("Clé plate 22mm", "Clé plate fourche 22mm", 6.0),
            ("Clé plate 24mm", "Clé plate fourche 24mm", 6.5),
            ("Jeu de clés plates", "Jeu complet 6–24mm", 25.0),
            # ── Clés à pipe / douilles ──
            ("Douille 8mm", "Douille 1/2\" – 8mm", 3.0),
            ("Douille 10mm", "Douille 1/2\" – 10mm", 3.0),
            ("Douille 13mm", "Douille 1/2\" – 13mm", 3.5),
            ("Douille 17mm", "Douille 1/2\" – 17mm", 4.0),
            ("Douille 19mm", "Douille 1/2\" – 19mm", 4.5),
            ("Douille 22mm", "Douille 1/2\" – 22mm", 5.0),
            ("Douille 24mm", "Douille 1/2\" – 24mm", 5.5),
            ("Jeu de clés à pipe", "Jeu clés à pipe / douilles complet", 30.0),
            # ── Clé à molette ──
            ("Clé à molette 150mm", "Clé ajustable 6\"", 12.0),
            ("Clé à molette 200mm", "Clé ajustable 8\"", 15.0),
            ("Clé à molette 250mm", "Clé ajustable 10\"", 18.0),
            ("Clé à molette 300mm", "Clé ajustable 12\"", 22.0),
            # ── Pinces ──
            ("Pince universelle", "Pince combinée", 10.0),
            ("Pince coupante", "Coupe-fil diagonal", 12.0),
            ("Pince à dénuder", "Dénudage fils 0.5–6mm²", 15.0),
            ("Pince à sertir", "Sertissage cosses / RJ45", 25.0),
            ("Pince multiprise", "Pince ajustable type Cobra", 18.0),
            ("Pince à bec long", "Pince demi-ronde", 10.0),
            # ── Divers ──
            ("Marteau", "Marteau menuisier / électricien", 12.0),
            ("Maillet caoutchouc", "Maillet non marquant", 10.0),
            ("Cutter", "Cutter à lame rétractable", 5.0),
            ("Ciseaux", "Ciseaux d'électricien", 8.0),
            ("Mètre ruban 5m", "Mètre enrouleur 5m", 6.0),
            ("Mètre ruban 8m", "Mètre enrouleur 8m", 10.0),
            ("Niveau à bulle", "Niveau 40–80cm", 15.0),
            ("Scie à métaux", "Scie manuelle", 12.0),
            ("Lime plate", "Lime plate bâtarde", 8.0),
            ("Lime ronde", "Lime ronde / queue-de-rat", 8.0),
        ],
    },
    "Outillage électroportatif": {
        "description": "Outils électriques portatifs",
        "icon": "drill",
        "types": [
            ("Visseuse sans fil 12V", "Visseuse compacte 12V", 90.0),
            ("Visseuse sans fil 18V", "Visseuse 18V brushless", 150.0),
            ("Perceuse à percussion", "Perceuse filaire ou sans fil", 150.0),
            ("Perforateur SDS+", "Perforateur SDS+ 800W", 200.0),
            ("Meuleuse 125mm", "Meuleuse d'angle 125mm", 80.0),
            ("Meuleuse 230mm", "Meuleuse d'angle 230mm", 120.0),
            ("Scie sauteuse", "Scie sauteuse pendulaire", 100.0),
            ("Scie circulaire", "Scie circulaire portative", 150.0),
            ("Ponceuse orbitale", "Ponceuse excentrique", 80.0),
            ("Décapeur thermique", "Pistolet à air chaud", 50.0),
            ("Fer à souder", "Station de soudage électronique", 60.0),
            ("Dremel / Multioutil", "Outil rotatif multifonction", 70.0),
            ("Pistolet à colle", "Pistolet à colle chaude", 20.0),
            # ── Embouts de visseuse ──
            ("Embout PH1", "Embout Phillips PH1 – 25mm", 1.0),
            ("Embout PH2", "Embout Phillips PH2 – 25mm", 1.0),
            ("Embout PH3", "Embout Phillips PH3 – 25mm", 1.0),
            ("Embout PZ1", "Embout Pozidriv PZ1 – 25mm", 1.0),
            ("Embout PZ2", "Embout Pozidriv PZ2 – 25mm", 1.0),
            ("Embout PZ3", "Embout Pozidriv PZ3 – 25mm", 1.0),
            ("Embout Torx T10", "Embout Torx T10 – 25mm", 1.5),
            ("Embout Torx T15", "Embout Torx T15 – 25mm", 1.5),
            ("Embout Torx T20", "Embout Torx T20 – 25mm", 1.5),
            ("Embout Torx T25", "Embout Torx T25 – 25mm", 1.5),
            ("Embout Torx T30", "Embout Torx T30 – 25mm", 1.5),
            ("Embout Torx T40", "Embout Torx T40 – 25mm", 1.5),
            ("Embout plat 4mm", "Embout plat 4mm – 25mm", 1.0),
            ("Embout plat 5.5mm", "Embout plat 5.5mm – 25mm", 1.0),
            ("Embout hex 3mm", "Embout hexagonal 3mm – 25mm", 1.5),
            ("Embout hex 4mm", "Embout hexagonal 4mm – 25mm", 1.5),
            ("Embout hex 5mm", "Embout hexagonal 5mm – 25mm", 1.5),
            ("Embout hex 6mm", "Embout hexagonal 6mm – 25mm", 1.5),
            ("Jeu d'embouts", "Coffret embouts 32 pièces", 15.0),
            # ── Forets ──
            ("Foret métal 2mm", "Foret HSS métal 2mm", 2.0),
            ("Foret métal 3mm", "Foret HSS métal 3mm", 2.0),
            ("Foret métal 4mm", "Foret HSS métal 4mm", 2.5),
            ("Foret métal 5mm", "Foret HSS métal 5mm", 3.0),
            ("Foret métal 6mm", "Foret HSS métal 6mm", 3.0),
            ("Foret métal 8mm", "Foret HSS métal 8mm", 4.0),
            ("Foret métal 10mm", "Foret HSS métal 10mm", 5.0),
            ("Foret béton 6mm", "Foret SDS / béton 6mm", 3.0),
            ("Foret béton 8mm", "Foret SDS / béton 8mm", 3.5),
            ("Foret béton 10mm", "Foret SDS / béton 10mm", 4.0),
            ("Foret béton 12mm", "Foret SDS / béton 12mm", 5.0),
            ("Foret bois 4mm", "Foret bois hélicoïdal 4mm", 2.0),
            ("Foret bois 6mm", "Foret bois hélicoïdal 6mm", 2.5),
            ("Foret bois 8mm", "Foret bois hélicoïdal 8mm", 3.0),
            ("Foret bois 10mm", "Foret bois hélicoïdal 10mm", 3.5),
            ("Jeu de forets", "Coffret forets métal/bois/béton", 20.0),
            # ── Douilles à choc ──
            ("Douille à choc 13mm", "Douille à choc 1/2\" – 13mm", 6.0),
            ("Douille à choc 17mm", "Douille à choc 1/2\" – 17mm", 7.0),
            ("Douille à choc 19mm", "Douille à choc 1/2\" – 19mm", 7.0),
            ("Douille à choc 22mm", "Douille à choc 1/2\" – 22mm", 8.0),
        ],
    },
    "Outillage de scène": {
        "description": "Outillage spécifique spectacle et événementiel",
        "icon": "stage",
        "types": [
            # ── Clés de pont (tailles courantes structure alu) ──
            ("Clé de pont 13mm", "Clé plate 13mm pour structures alu", 8.0),
            ("Clé de pont 17mm", "Clé plate 17mm pour structures alu", 10.0),
            ("Clé de pont 19mm", "Clé plate 19mm pour structures alu", 10.0),
            ("Clé de pont double 13/17", "Clé double 13/17mm", 15.0),
            ("Clé de pont double 17/19", "Clé double 17/19mm", 15.0),
            ("Clé de pont triple 13/17/19", "Clé triple structures", 25.0),
            # ── Clés à cliquet ──
            ("Cliquet 1/4\"", "Cliquet 1/4 pouce", 25.0),
            ("Cliquet 3/8\"", "Cliquet 3/8 pouce", 28.0),
            ("Cliquet 1/2\"", "Cliquet 1/2 pouce", 30.0),
            ("Rallonge cliquet 1/2\"", "Rallonge 125mm pour cliquet", 8.0),
            # ── Accroche / Levage ──
            ("Manille droite 0.5T", "Manille acier galvanisé 0.5T", 5.0),
            ("Manille droite 1T", "Manille acier galvanisé 1T", 8.0),
            ("Manille droite 2T", "Manille acier galvanisé 2T", 12.0),
            ("Manille lyrique 0.5T", "Manille de levage 0.5T", 8.0),
            ("Manille lyrique 1T", "Manille de levage 1T", 12.0),
            ("Élingue textile 1T", "Élingue ronde 1T – 1m", 15.0),
            ("Élingue textile 2T", "Élingue ronde 2T – 2m", 25.0),
            ("Élingue textile 5T", "Élingue ronde 5T – 3m", 40.0),
            ("Élingue câble acier", "Élingue avec boucles", 40.0),
            ("Crochet de pont", "Crochet pour structure alu", 20.0),
            ("Coupleur pivotant", "Coupleur 48–51mm", 12.0),
            ("Coupleur fixe", "Coupleur 48–51mm", 10.0),
            ("Serre-câble", "Serre-câble acier", 3.0),
            ("Clé dynamométrique", "Clé à couple réglable", 80.0),
            ("Pince de serrage", "Trigger clamp / serre-joint", 15.0),
            ("Chaîne de sécurité", "Chaîne de retenue", 10.0),
        ],
    },
    "Fixation": {
        "description": "Visserie, colliers, sangles de fixation",
        "icon": "screw",
        "types": [
            # ── Vis ──
            ("Vis auto-perceuse 4.2×13", "Vis TEK 4.2×13mm", 0.08),
            ("Vis auto-perceuse 4.2×19", "Vis TEK 4.2×19mm", 0.08),
            ("Vis auto-perceuse 4.8×25", "Vis TEK 4.8×25mm", 0.10),
            ("Vis à bois 3.5×30", "Vis bois 3.5×30mm", 0.05),
            ("Vis à bois 4×40", "Vis bois 4×40mm", 0.06),
            ("Vis à bois 4.5×50", "Vis bois 4.5×50mm", 0.08),
            ("Vis à bois 5×60", "Vis bois 5×60mm", 0.10),
            ("Vis à bois 6×80", "Vis bois 6×80mm", 0.14),
            # ── Boulonnerie métrique ──
            ("Vis M4×20", "Vis CHC / TH M4×20", 0.10),
            ("Vis M5×25", "Vis CHC / TH M5×25", 0.12),
            ("Vis M6×20", "Vis CHC / TH M6×20", 0.15),
            ("Vis M6×40", "Vis CHC / TH M6×40", 0.18),
            ("Vis M8×30", "Vis CHC / TH M8×30", 0.20),
            ("Vis M8×50", "Vis CHC / TH M8×50", 0.25),
            ("Vis M10×40", "Vis CHC / TH M10×40", 0.30),
            ("Vis M10×60", "Vis CHC / TH M10×60", 0.35),
            ("Boulon M6×30", "Boulon M6 + écrou + rondelle", 0.35),
            ("Boulon M8×40", "Boulon M8 + écrou + rondelle", 0.45),
            ("Boulon M10×50", "Boulon M10 + écrou + rondelle", 0.60),
            ("Boulon M12×60", "Boulon M12 + écrou + rondelle", 0.80),
            # ── Écrous / Rondelles ──
            ("Écrou nylstop M6", "Écrou auto-freiné M6", 0.10),
            ("Écrou nylstop M8", "Écrou auto-freiné M8", 0.12),
            ("Écrou nylstop M10", "Écrou auto-freiné M10", 0.15),
            ("Rondelle plate M6", "Rondelle acier zingué M6", 0.03),
            ("Rondelle plate M8", "Rondelle acier zingué M8", 0.04),
            ("Rondelle plate M10", "Rondelle acier zingué M10", 0.05),
            # ── Colliers et sangles ──
            ("Collier nylon 200mm", "Rilsan 200×3.6mm", 0.03),
            ("Collier nylon 300mm", "Rilsan 300×4.8mm", 0.05),
            ("Collier nylon 370mm", "Rilsan 370×4.8mm", 0.06),
            ("Collier métallique", "Collier inox à vis", 1.00),
            ("Sangle à cliquet 25mm", "Sangle d'arrimage 25mm – 5m", 8.0),
            ("Sangle à cliquet 50mm", "Sangle d'arrimage 50mm – 6m", 12.0),
            ("Velcro", "Rouleau velcro double-face", 5.0),
            ("Inserts filetés M6", "Insert à visser M6", 0.40),
            ("Inserts filetés M8", "Insert à visser M8", 0.50),
            ("Cheville 6mm", "Cheville béton / placo 6mm", 0.15),
            ("Cheville 8mm", "Cheville béton / placo 8mm", 0.20),
            ("Cheville 10mm", "Cheville béton / placo 10mm", 0.30),
        ],
    },
    "Test / Mesure": {
        "description": "Appareils de test et de mesure",
        "icon": "meter",
        "types": [
            ("Multimètre", "Multimètre numérique", 50.0),
            ("Testeur de câble réseau", "Testeur RJ45 / RJ11", 40.0),
            ("Testeur XLR", "Testeur de câble audio XLR", 35.0),
            ("Testeur DMX", "Testeur / analyseur DMX512", 80.0),
            ("Testeur de phase", "Tournevis testeur 230V", 5.0),
            ("Pince ampèremétrique", "Mesure courant AC/DC sans contact", 60.0),
            ("Sonomètre", "Mesure niveau sonore dB", 80.0),
            ("Luxmètre", "Mesure éclairement lux", 50.0),
            ("Thermomètre IR", "Thermomètre infrarouge sans contact", 30.0),
            ("Télémètre laser", "Mesure distance laser", 50.0),
            ("Détecteur de métaux", "Scanner mural câbles / tuyaux", 40.0),
        ],
    },
    "Entretien / Nettoyage": {
        "description": "Produits et outillage d'entretien",
        "icon": "clean",
        "types": [
            ("Bombe air comprimé", "Dépoussiérant aérosol", 8.0),
            ("Nettoyant contact", "Spray nettoyant électronique", 10.0),
            ("Dégrippant (WD-40)", "Lubrifiant dégrippant", 8.0),
            ("Lingettes antistatiques", "Lingettes pour écrans / optiques", 6.0),
            ("Aspirateur atelier", "Aspirateur eau et poussière", 120.0),
            ("Balai / Pelle", "Kit balai + pelle", 10.0),
            ("Chiffons microfibres", "Lot chiffons doux", 5.0),
            ("Graisse", "Graisse silicone / mécanique", 10.0),
        ],
    },
    "Rangement / Transport": {
        "description": "Solutions de rangement et transport",
        "icon": "box",
        "types": [
            ("Flight-case", "Flight-case sur mesure / standard", 200.0),
            ("Valise d'outillage", "Valise rigide garnie", 80.0),
            ("Caisse plastique", "Bac de rangement empilable", 15.0),
            ("Organiseur", "Boîte à compartiments", 12.0),
            ("Chariot de transport", "Chariot à roulettes", 150.0),
            ("Diable", "Diable de manutention", 80.0),
            ("Sacoche ceinture", "Porte-outils de ceinture", 25.0),
            ("Rack 19 pouces", "Rack mobile / fixe", 300.0),
            ("Housse de protection", "Housse matelassée", 30.0),
        ],
    },
}


def _seed_tool_catalog(conn: sqlite3.Connection):
    """Pré-remplit le catalogue outillage et ajoute les nouveaux types manquants."""
    if not _table_exists_in(conn, "tool_categories"):
        return

    existing_cats = {
        row[0]: row[1]
        for row in conn.execute("SELECT name, id FROM tool_categories").fetchall()
    }
    added = 0

    for cat_name, cat_data in _TOOL_CATALOG.items():
        if cat_name in existing_cats:
            cat_id = existing_cats[cat_name]
        else:
            cur = conn.execute(
                "INSERT INTO tool_categories (name, description, icon) VALUES (?,?,?)",
                (cat_name, cat_data["description"], cat_data.get("icon", "")),
            )
            cat_id = cur.lastrowid

        # Récupérer les noms de types existants pour cette catégorie
        existing_types = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM tool_types WHERE category_id = ?", (cat_id,)
            ).fetchall()
        }

        for type_name, type_desc, price in cat_data["types"]:
            if type_name not in existing_types:
                conn.execute(
                    "INSERT INTO tool_types (category_id, name, description, default_ref, default_price) "
                    "VALUES (?,?,?,?,?)",
                    (cat_id, type_name, type_desc, "", price),
                )
                added += 1

    if added:
        print(f"  [Seed] Catalogue outillage : {added} nouveaux types ajoutés")


def _table_exists_in(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row[0] > 0
