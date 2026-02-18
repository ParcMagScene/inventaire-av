"""
models.py — Dataclasses représentant les entités métier.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Category:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    default_price: float = 0.0


@dataclass
class Location:
    id: Optional[int] = None
    name: str = ""
    description: str = ""


@dataclass
class Supplier:
    id: Optional[int] = None
    name: str = ""
    contact: str = ""
    email: str = ""
    phone: str = ""
    profile: str = "moyen"          # economique / moyen / cher
    notes: str = ""


@dataclass
class Article:
    id: Optional[int] = None
    reference: str = ""
    name: str = ""
    description: str = ""
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: int = 0
    quantity_min: int = 0
    price_mode: str = "automatique"   # manuel / automatique / mixte
    price_avg: float = 0.0
    price_low: float = 0.0
    price_high: float = 0.0
    price_manual: Optional[float] = None
    price_manual_low: Optional[float] = None
    price_manual_high: Optional[float] = None
    confidence: str = "faible"        # faible / moyen / fort
    price_source: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Relations chargées dynamiquement
    category_name: str = ""
    location_name: str = ""
    supplier_name: str = ""


@dataclass
class PriceRule:
    id: Optional[int] = None
    key: str = ""
    value: float = 0.0
    description: str = ""


@dataclass
class CategoryPriceMode:
    id: Optional[int] = None
    category_id: Optional[int] = None
    price_mode: str = "automatique"


@dataclass
class ReferencePriceMode:
    id: Optional[int] = None
    reference: str = ""
    price_mode: str = "automatique"
    fixed_price: float = 0.0


@dataclass
class PriceHistory:
    id: Optional[int] = None
    article_id: Optional[int] = None
    price: float = 0.0
    quantity: int = 1
    supplier_id: Optional[int] = None
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""


@dataclass
class PriceSuggestion:
    """Résultat renvoyé par le moteur de prix."""
    avg_price: float = 0.0
    low_price: float = 0.0
    high_price: float = 0.0
    confidence: str = "faible"
    source: str = ""
    explanation: str = ""
