"""
totals_engine.py — Module de calcul des totaux globaux dynamiques.

Fournit des totaux par catégorie, emplacement, fournisseur et mode de prix,
ainsi que les totaux globaux (bas / moyen / haut / actif).
"""
from typing import List, Dict, Any
from .models import Article
from . import database as db


class TotalsEngine:
    """Calcul dynamique de tous les totaux de l'inventaire."""

    def __init__(self, db_path=None):
        self.db_path = db_path

    # ─── Totaux globaux ──────────────────────────────
    def global_totals(self, articles: List[Article] | None = None) -> dict:
        """Totaux globaux bas / moyen / haut / actif."""
        if articles is None:
            articles = db.get_articles(self.db_path)
        return {
            "nb_references": len(articles),
            "total_quantity": sum(a.quantity for a in articles),
            "total_low": round(sum(a.total_low for a in articles), 2),
            "total_avg": round(sum(a.total_avg for a in articles), 2),
            "total_high": round(sum(a.total_high for a in articles), 2),
            "total_active": round(sum(a.total_active for a in articles), 2),
        }

    # ─── Totaux par catégorie ────────────────────────
    def totals_by_category(self, articles: List[Article] | None = None) -> Dict[str, dict]:
        if articles is None:
            articles = db.get_articles(self.db_path)
        result: Dict[str, dict] = {}
        for a in articles:
            key = a.category_name or "Sans catégorie"
            if key not in result:
                result[key] = {"qty": 0, "low": 0.0, "avg": 0.0, "high": 0.0, "active": 0.0}
            result[key]["qty"] += a.quantity
            result[key]["low"] += a.total_low
            result[key]["avg"] += a.total_avg
            result[key]["high"] += a.total_high
            result[key]["active"] += a.total_active
        # Arrondir
        for v in result.values():
            v["low"] = round(v["low"], 2)
            v["avg"] = round(v["avg"], 2)
            v["high"] = round(v["high"], 2)
            v["active"] = round(v["active"], 2)
        return result

    # ─── Totaux par emplacement ──────────────────────
    def totals_by_location(self, articles: List[Article] | None = None) -> Dict[str, dict]:
        if articles is None:
            articles = db.get_articles(self.db_path)
        result: Dict[str, dict] = {}
        for a in articles:
            key = a.location_name or "Sans emplacement"
            if key not in result:
                result[key] = {"qty": 0, "low": 0.0, "avg": 0.0, "high": 0.0, "active": 0.0}
            result[key]["qty"] += a.quantity
            result[key]["low"] += a.total_low
            result[key]["avg"] += a.total_avg
            result[key]["high"] += a.total_high
            result[key]["active"] += a.total_active
        for v in result.values():
            v["low"] = round(v["low"], 2)
            v["avg"] = round(v["avg"], 2)
            v["high"] = round(v["high"], 2)
            v["active"] = round(v["active"], 2)
        return result

    # ─── Totaux par fournisseur ──────────────────────
    def totals_by_supplier(self, articles: List[Article] | None = None) -> Dict[str, dict]:
        if articles is None:
            articles = db.get_articles(self.db_path)
        result: Dict[str, dict] = {}
        for a in articles:
            key = a.supplier_name or "Sans fournisseur"
            if key not in result:
                result[key] = {"qty": 0, "low": 0.0, "avg": 0.0, "high": 0.0, "active": 0.0}
            result[key]["qty"] += a.quantity
            result[key]["low"] += a.total_low
            result[key]["avg"] += a.total_avg
            result[key]["high"] += a.total_high
            result[key]["active"] += a.total_active
        for v in result.values():
            v["low"] = round(v["low"], 2)
            v["avg"] = round(v["avg"], 2)
            v["high"] = round(v["high"], 2)
            v["active"] = round(v["active"], 2)
        return result

    # ─── Totaux par mode de prix ─────────────────────
    def totals_by_price_mode(self, articles: List[Article] | None = None) -> Dict[str, dict]:
        if articles is None:
            articles = db.get_articles(self.db_path)
        result: Dict[str, dict] = {}
        for a in articles:
            key = a.price_mode or "non défini"
            if key not in result:
                result[key] = {"qty": 0, "count": 0, "low": 0.0, "avg": 0.0, "high": 0.0}
            result[key]["count"] += 1
            result[key]["qty"] += a.quantity
            result[key]["low"] += a.total_low
            result[key]["avg"] += a.total_avg
            result[key]["high"] += a.total_high
        for v in result.values():
            v["low"] = round(v["low"], 2)
            v["avg"] = round(v["avg"], 2)
            v["high"] = round(v["high"], 2)
        return result

    # ─── Alertes stock bas ───────────────────────────
    def low_stock_alerts(self, articles: List[Article] | None = None) -> List[Article]:
        """Retourne les articles dont le stock est en dessous du seuil minimum."""
        if articles is None:
            articles = db.get_articles(self.db_path)
        return [a for a in articles if a.is_low_stock]

    # ─── Articles avec prix incohérents ──────────────
    def inconsistent_prices(self, articles: List[Article] | None = None) -> List[Article]:
        """Retourne les articles dont les prix sont incohérents."""
        if articles is None:
            articles = db.get_articles(self.db_path)
        return [a for a in articles if a.is_price_inconsistent]

    # ─── Résumé complet ─────────────────────────────
    def full_summary(self, articles: List[Article] | None = None) -> dict:
        """Résumé complet de tous les totaux pour le dashboard et l'export."""
        if articles is None:
            articles = db.get_articles(self.db_path)
        return {
            "global": self.global_totals(articles),
            "by_category": self.totals_by_category(articles),
            "by_location": self.totals_by_location(articles),
            "by_supplier": self.totals_by_supplier(articles),
            "by_price_mode": self.totals_by_price_mode(articles),
            "low_stock_count": len(self.low_stock_alerts(articles)),
            "inconsistent_count": len(self.inconsistent_prices(articles)),
        }
