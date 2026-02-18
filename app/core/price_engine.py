"""
price_engine.py — Moteur intelligent de suggestion de prix.

Sources (par ordre de priorité) :
 1. Référence fixe (reference_price_modes)
 2. Historique interne (moyenne pondérée, exclusion aberrations)
 3. Fournisseur (profil économique / moyen / cher)
 4. Catégorie (médiane des prix de la catégorie)
 5. Prix par défaut de la catégorie
"""
import math
import statistics
from datetime import datetime, timedelta
from typing import List, Optional

from . import database as db
from .models import Article, PriceHistory, PriceSuggestion


class PriceEngine:
    """Calcule un prix moyen suggéré avec confiance et explication."""

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._rules: dict = {}
        self._reload_rules()

    # ─── helpers ──────────────────────────────────────
    def _reload_rules(self):
        self._rules = db.get_price_rules(self.db_path)

    def _rule(self, key: str, default: float = 0.0) -> float:
        return self._rules.get(key, default)

    # ─── point d'entrée ───────────────────────────────
    def suggest(self, article: Article) -> PriceSuggestion:
        """Renvoie la suggestion de prix pour un article donné."""
        self._reload_rules()

        # 1. Référence fixe
        ref_result = self._from_reference(article)
        if ref_result:
            return ref_result

        # 2. Historique
        hist_result = self._from_history(article)

        # 3. Fournisseur
        supplier_result = self._from_supplier(article)

        # 4. Catégorie (médiane)
        cat_result = self._from_category(article)

        # 5. Par défaut catégorie
        default_result = self._from_default(article)

        # Fusion pondérée
        return self._merge(article, hist_result, supplier_result, cat_result, default_result)

    # ─── source 1 : référence ────────────────────────
    def _from_reference(self, article: Article) -> Optional[PriceSuggestion]:
        refs = db.get_reference_price_modes(self.db_path)
        for r in refs:
            if r.reference == article.reference and r.fixed_price > 0:
                low_f = self._rule("price_low_factor", 0.80)
                high_f = self._rule("price_high_factor", 1.25)
                return PriceSuggestion(
                    avg_price=round(r.fixed_price, 2),
                    low_price=round(r.fixed_price * low_f, 2),
                    high_price=round(r.fixed_price * high_f, 2),
                    confidence="fort",
                    source="reference",
                    explanation=f"Prix fixé par référence : {r.fixed_price:.2f} €",
                )
        return None

    # ─── source 2 : historique pondéré ────────────────
    def _from_history(self, article: Article) -> Optional[PriceSuggestion]:
        if article.id is None:
            return None
        entries: List[PriceHistory] = db.get_price_history(article.id, self.db_path)
        if not entries:
            return None

        decay_days = self._rule("history_decay_days", 180)
        sigma = self._rule("outlier_sigma", 2.0)
        now = datetime.now()

        prices = [e.price for e in entries if e.price > 0]
        if len(prices) < 2:
            if prices:
                avg = prices[0]
                return self._build_suggestion(avg, "historique",
                                              f"Une seule entrée historique : {avg:.2f} €",
                                              "faible")
            return None

        # Exclusion des aberrations (méthode sigma)
        mean = statistics.mean(prices)
        std = statistics.stdev(prices)
        if std > 0:
            filtered = [(e.price, e.quantity, e.date) for e in entries
                        if abs(e.price - mean) <= sigma * std and e.price > 0]
        else:
            filtered = [(e.price, e.quantity, e.date) for e in entries if e.price > 0]

        if not filtered:
            filtered = [(e.price, e.quantity, e.date) for e in entries if e.price > 0]

        # Pondération temporelle + volume
        weighted_sum = 0.0
        weight_total = 0.0
        for price, qty, date_str in filtered:
            try:
                dt = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                dt = now
            age_days = max((now - dt).days, 0)
            time_weight = math.exp(-age_days / max(decay_days, 1))
            vol_weight = max(qty, 1)
            w = time_weight * vol_weight
            weighted_sum += price * w
            weight_total += w

        if weight_total == 0:
            return None

        avg = weighted_sum / weight_total
        n = len(filtered)
        min_hist = int(self._rule("min_history_entries", 3))
        confidence = "fort" if n >= min_hist * 2 else ("moyen" if n >= min_hist else "faible")

        return self._build_suggestion(
            avg, "historique",
            f"Moyenne pondérée sur {n} entrées historiques : {avg:.2f} €",
            confidence,
        )

    # ─── source 3 : fournisseur ──────────────────────
    def _from_supplier(self, article: Article) -> Optional[PriceSuggestion]:
        if not article.supplier_id:
            return None
        suppliers = db.get_suppliers(self.db_path)
        supplier = next((s for s in suppliers if s.id == article.supplier_id), None)
        if not supplier:
            return None
        profile_key = f"supplier_{supplier.profile}"
        factor = self._rule(profile_key, 1.0)
        # On a besoin d'un prix de base pour appliquer le facteur
        # → on utilise le défaut catégorie
        categories = db.get_categories(self.db_path)
        cat = next((c for c in categories if c.id == article.category_id), None)
        if not cat or cat.default_price <= 0:
            return None
        avg = cat.default_price * factor
        return self._build_suggestion(
            avg, "fournisseur",
            f"Profil fournisseur « {supplier.profile} » appliqué au défaut catégorie : {avg:.2f} €",
            "moyen",
        )

    # ─── source 4 : catégorie (médiane) ──────────────
    def _from_category(self, article: Article) -> Optional[PriceSuggestion]:
        if not article.category_id:
            return None
        articles = db.get_articles(self.db_path, category_id=article.category_id)
        prices = [a.price_avg for a in articles if a.price_avg > 0 and a.id != article.id]
        if not prices:
            return None
        med = statistics.median(prices)
        return self._build_suggestion(
            med, "catégorie",
            f"Médiane de {len(prices)} articles de la même catégorie : {med:.2f} €",
            "moyen" if len(prices) >= 3 else "faible",
        )

    # ─── source 5 : défaut ──────────────────────────
    def _from_default(self, article: Article) -> Optional[PriceSuggestion]:
        if not article.category_id:
            return None
        categories = db.get_categories(self.db_path)
        cat = next((c for c in categories if c.id == article.category_id), None)
        if not cat or cat.default_price <= 0:
            return None
        return self._build_suggestion(
            cat.default_price, "défaut",
            f"Prix par défaut de la catégorie « {cat.name} » : {cat.default_price:.2f} €",
            "faible",
        )

    # ─── fusion pondérée ─────────────────────────────
    def _merge(self, article: Article,
               hist: Optional[PriceSuggestion],
               supplier: Optional[PriceSuggestion],
               cat: Optional[PriceSuggestion],
               default: Optional[PriceSuggestion]) -> PriceSuggestion:
        candidates = []
        weight_map = {
            "historique": self._rule("weight_history", 0.8),
            "fournisseur": self._rule("weight_supplier", 0.6),
            "catégorie": self._rule("weight_category", 0.5),
            "défaut": self._rule("weight_default", 0.2),
        }
        for s in (hist, supplier, cat, default):
            if s and s.avg_price > 0:
                candidates.append(s)

        if not candidates:
            return PriceSuggestion(
                explanation="Aucune donnée disponible pour suggérer un prix.",
                confidence="faible",
                source="aucune",
            )

        # Sélection du meilleur candidat ou fusion
        if len(candidates) == 1:
            return candidates[0]

        # Fusion pondérée
        total_w = 0.0
        weighted_price = 0.0
        best = candidates[0]
        best_weight = 0.0
        for c in candidates:
            w = weight_map.get(c.source, 0.3)
            # Boost si confiance forte
            if c.confidence == "fort":
                w *= 1.5
            elif c.confidence == "moyen":
                w *= 1.2
            weighted_price += c.avg_price * w
            total_w += w
            if w > best_weight:
                best_weight = w
                best = c

        avg = weighted_price / total_w if total_w > 0 else 0
        # Confiance globale
        conf_scores = {"fort": 3, "moyen": 2, "faible": 1}
        avg_conf = statistics.mean([conf_scores.get(c.confidence, 1) for c in candidates])
        if avg_conf >= 2.5:
            confidence = "fort"
        elif avg_conf >= 1.5:
            confidence = "moyen"
        else:
            confidence = "faible"

        sources = ", ".join(c.source for c in candidates)
        return self._build_suggestion(
            avg, best.source,
            f"Fusion pondérée ({sources}) → {avg:.2f} € (source principale : {best.source})",
            confidence,
        )

    # ─── utilitaire ──────────────────────────────────
    def _build_suggestion(self, avg: float, source: str,
                          explanation: str, confidence: str) -> PriceSuggestion:
        low_f = self._rule("price_low_factor", 0.80)
        high_f = self._rule("price_high_factor", 1.25)
        return PriceSuggestion(
            avg_price=round(avg, 2),
            low_price=round(avg * low_f, 2),
            high_price=round(avg * high_f, 2),
            confidence=confidence,
            source=source,
            explanation=explanation,
        )

    # ─── application selon le mode ────────────────────
    def apply_price(self, article: Article) -> Article:
        """Met à jour les prix de l'article selon son mode de prix."""
        suggestion = self.suggest(article)

        if article.price_mode == "manuel":
            # En mode manuel, on garde les prix manuels
            article.price_avg = article.price_manual or 0.0
            article.price_low = article.price_manual_low or 0.0
            article.price_high = article.price_manual_high or 0.0
            article.confidence = "fort"
            article.price_source = "Manuel"

        elif article.price_mode == "automatique":
            article.price_avg = suggestion.avg_price
            article.price_low = suggestion.low_price
            article.price_high = suggestion.high_price
            article.confidence = suggestion.confidence
            article.price_source = suggestion.explanation

        elif article.price_mode == "mixte":
            # Priorité : référence > catégorie > prix moyen
            ref = self._from_reference(article)
            if ref:
                article.price_avg = ref.avg_price
                article.price_low = ref.low_price
                article.price_high = ref.high_price
                article.confidence = ref.confidence
                article.price_source = ref.explanation
            else:
                cat = self._from_category(article)
                if cat and cat.avg_price > 0:
                    article.price_avg = cat.avg_price
                    article.price_low = cat.low_price
                    article.price_high = cat.high_price
                    article.confidence = cat.confidence
                    article.price_source = cat.explanation
                else:
                    article.price_avg = suggestion.avg_price
                    article.price_low = suggestion.low_price
                    article.price_high = suggestion.high_price
                    article.confidence = suggestion.confidence
                    article.price_source = suggestion.explanation

        return article
