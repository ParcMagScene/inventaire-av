"""
price_engine.py — Moteur intelligent de suggestion de prix.

Sources (par ordre de priorité) :
 1. Référence fixe (reference_price_modes)
 2. Historique interne (moyenne pondérée, exclusion aberrations)
 3. Fournisseur (profil économique / moyen / cher)
 4. Catégorie (médiane des prix de la catégorie)
 5. Prix par défaut de la catégorie

Améliorations v2 :
 - Détection d'anomalies (IQR + sigma)
 - Exclusion automatique des valeurs extrêmes
 - Pondération temporelle améliorée (décroissance exponentielle)
 - Pondération par volume
 - Score de confiance 0–100
 - Explication détaillée de la source principale
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
        merged = self._merge(article, hist_result, supplier_result, cat_result, default_result)

        # Détection d'anomalies sur le résultat final
        anomalies = self._detect_anomalies(article, merged)
        merged.anomalies = anomalies

        return merged

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
                    confidence_score=95,
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
                                              "faible", confidence_score=15)
            return None

        # Exclusion des aberrations (méthode IQR + sigma combinée)
        filtered_entries = self._filter_outliers(entries, sigma)

        if not filtered_entries:
            filtered_entries = [(e.price, e.quantity, e.date) for e in entries if e.price > 0]

        # Pondération temporelle améliorée + volume
        weighted_sum = 0.0
        weight_total = 0.0
        for price, qty, date_str in filtered_entries:
            try:
                dt = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                dt = now
            age_days = max((now - dt).days, 0)
            # Décroissance exponentielle améliorée
            time_weight = math.exp(-age_days / max(decay_days, 1))
            # Pondération par volume (racine carrée pour atténuer l'effet)
            vol_weight = math.sqrt(max(qty, 1))
            w = time_weight * vol_weight
            weighted_sum += price * w
            weight_total += w

        if weight_total == 0:
            return None

        avg = weighted_sum / weight_total
        n = len(filtered_entries)
        n_total = len(prices)
        min_hist = int(self._rule("min_history_entries", 3))

        # Score de confiance basé sur le nombre d'entrées et la fraîcheur
        score = self._compute_confidence_score(
            n_entries=n, min_entries=min_hist,
            entries=entries, decay_days=decay_days
        )
        confidence = self._score_to_label(score)

        excluded = n_total - n
        excl_msg = f" ({excluded} aberrations exclues)" if excluded > 0 else ""
        return self._build_suggestion(
            avg, "historique",
            f"Moyenne pondérée sur {n}/{n_total} entrées historiques : {avg:.2f} €{excl_msg}",
            confidence, confidence_score=score,
        )

    # ─── Filtrage des aberrations (IQR + sigma) ──────
    def _filter_outliers(self, entries: List[PriceHistory],
                         sigma: float) -> list:
        """Filtre les aberrations avec la méthode IQR et sigma combinées."""
        prices = [e.price for e in entries if e.price > 0]
        if len(prices) < 3:
            return [(e.price, e.quantity, e.date) for e in entries if e.price > 0]

        mean = statistics.mean(prices)
        std = statistics.stdev(prices)

        # Méthode IQR (interquartile range)
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        q1 = sorted_prices[n // 4]
        q3 = sorted_prices[(3 * n) // 4]
        iqr = q3 - q1
        iqr_low = q1 - 1.5 * iqr
        iqr_high = q3 + 1.5 * iqr

        filtered = []
        for e in entries:
            if e.price <= 0:
                continue
            # Exclure si hors IQR ET hors sigma
            in_sigma = (std == 0) or (abs(e.price - mean) <= sigma * std)
            in_iqr = iqr_low <= e.price <= iqr_high
            if in_sigma or in_iqr:
                filtered.append((e.price, e.quantity, e.date))

        return filtered if filtered else [(e.price, e.quantity, e.date)
                                          for e in entries if e.price > 0]

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
            "moyen", confidence_score=45,
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
        n = len(prices)
        score = min(60, 20 + n * 8)  # Plus d'articles = plus de confiance
        return self._build_suggestion(
            med, "catégorie",
            f"Médiane de {n} articles de la même catégorie : {med:.2f} €",
            "moyen" if n >= 3 else "faible",
            confidence_score=score,
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
            "faible", confidence_score=10,
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
                confidence_score=0,
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

        # Score de confiance global pondéré
        score_weighted = sum(
            c.confidence_score * weight_map.get(c.source, 0.3)
            for c in candidates
        )
        total_source_w = sum(weight_map.get(c.source, 0.3) for c in candidates)
        global_score = int(score_weighted / total_source_w) if total_source_w > 0 else 0
        # Bonus pour sources multiples
        global_score = min(100, global_score + len(candidates) * 5)
        confidence = self._score_to_label(global_score)

        sources = ", ".join(c.source for c in candidates)
        return self._build_suggestion(
            avg, best.source,
            f"Fusion pondérée ({sources}) → {avg:.2f} € "
            f"(source principale : {best.source}, score : {global_score}/100)",
            confidence, confidence_score=global_score,
        )

    # ─── Détection d'anomalies ───────────────────────
    def _detect_anomalies(self, article: Article,
                          suggestion: PriceSuggestion) -> list:
        """Détecte les incohérences dans les prix."""
        anomalies = []
        if suggestion.avg_price <= 0:
            return anomalies

        # Prix bas > prix moyen
        if suggestion.low_price > suggestion.avg_price:
            anomalies.append("Prix bas supérieur au prix moyen")

        # Prix moyen > prix haut
        if suggestion.avg_price > suggestion.high_price:
            anomalies.append("Prix moyen supérieur au prix haut")

        # Écart trop important entre bas et haut (> 5x)
        if suggestion.low_price > 0:
            ratio = suggestion.high_price / suggestion.low_price
            if ratio > 5:
                anomalies.append(
                    f"Écart prix bas/haut très élevé (×{ratio:.1f})"
                )

        # Prix manuel très éloigné du prix suggéré
        if article.price_manual and article.price_manual > 0:
            diff_pct = abs(article.price_manual - suggestion.avg_price) / suggestion.avg_price * 100
            if diff_pct > 50:
                anomalies.append(
                    f"Prix manuel ({article.price_manual:.2f} €) éloigné de "
                    f"{diff_pct:.0f}% du prix suggéré ({suggestion.avg_price:.2f} €)"
                )

        return anomalies

    # ─── Score de confiance 0–100 ────────────────────
    def _compute_confidence_score(self, n_entries: int, min_entries: int,
                                  entries: List[PriceHistory],
                                  decay_days: float) -> int:
        """Calcule un score de confiance 0–100 basé sur plusieurs facteurs."""
        score = 0.0
        now = datetime.now()

        # Factor 1 : Nombre d'entrées (0–40 points)
        if n_entries >= min_entries * 3:
            score += 40
        elif n_entries >= min_entries * 2:
            score += 30
        elif n_entries >= min_entries:
            score += 20
        elif n_entries >= 2:
            score += 10
        elif n_entries >= 1:
            score += 5

        # Factor 2 : Fraîcheur des données (0–30 points)
        if entries:
            try:
                most_recent = max(
                    datetime.fromisoformat(e.date) for e in entries
                    if e.date
                )
                age = (now - most_recent).days
                if age <= 30:
                    score += 30
                elif age <= 90:
                    score += 20
                elif age <= 180:
                    score += 10
                elif age <= 365:
                    score += 5
            except (ValueError, TypeError):
                pass

        # Factor 3 : Cohérence des prix (0–20 points)
        prices = [e.price for e in entries if e.price > 0]
        if len(prices) >= 2:
            mean = statistics.mean(prices)
            cv = statistics.stdev(prices) / mean if mean > 0 else 1
            if cv < 0.1:
                score += 20  # Très cohérent
            elif cv < 0.2:
                score += 15
            elif cv < 0.3:
                score += 10
            elif cv < 0.5:
                score += 5

        # Factor 4 : Volume total traité (0–10 points)
        total_vol = sum(e.quantity for e in entries)
        if total_vol >= 100:
            score += 10
        elif total_vol >= 50:
            score += 7
        elif total_vol >= 10:
            score += 5
        elif total_vol >= 3:
            score += 3

        return min(100, int(score))

    # ─── utilitaires ─────────────────────────────────
    @staticmethod
    def _score_to_label(score: int) -> str:
        """Convertit un score numérique en label textuel."""
        if score >= 70:
            return "fort"
        elif score >= 40:
            return "moyen"
        else:
            return "faible"

    def _build_suggestion(self, avg: float, source: str,
                          explanation: str, confidence: str,
                          confidence_score: int = 0) -> PriceSuggestion:
        low_f = self._rule("price_low_factor", 0.80)
        high_f = self._rule("price_high_factor", 1.25)
        return PriceSuggestion(
            avg_price=round(avg, 2),
            low_price=round(avg * low_f, 2),
            high_price=round(avg * high_f, 2),
            confidence=confidence,
            confidence_score=confidence_score,
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
            article.confidence_score = 90
            article.price_source = "Manuel"

        elif article.price_mode == "automatique":
            article.price_avg = suggestion.avg_price
            article.price_low = suggestion.low_price
            article.price_high = suggestion.high_price
            article.confidence = suggestion.confidence
            article.confidence_score = suggestion.confidence_score
            article.price_source = suggestion.explanation

        elif article.price_mode == "mixte":
            # Priorité : référence > catégorie > prix moyen
            ref = self._from_reference(article)
            if ref:
                article.price_avg = ref.avg_price
                article.price_low = ref.low_price
                article.price_high = ref.high_price
                article.confidence = ref.confidence
                article.confidence_score = ref.confidence_score
                article.price_source = ref.explanation
            else:
                cat = self._from_category(article)
                if cat and cat.avg_price > 0:
                    article.price_avg = cat.avg_price
                    article.price_low = cat.low_price
                    article.price_high = cat.high_price
                    article.confidence = cat.confidence
                    article.confidence_score = cat.confidence_score
                    article.price_source = cat.explanation
                else:
                    article.price_avg = suggestion.avg_price
                    article.price_low = suggestion.low_price
                    article.price_high = suggestion.high_price
                    article.confidence = suggestion.confidence
                    article.confidence_score = suggestion.confidence_score
                    article.price_source = suggestion.explanation

        # Ajouter info anomalies dans la source si détectées
        if suggestion.anomalies:
            article.price_source += f" ⚠ Anomalies : {', '.join(suggestion.anomalies)}"

        return article
