"""
inventory_view.py — Vue principale de l'inventaire des articles.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QGroupBox, QGridLayout, QComboBox,
)

from ...core import database as db
from ...core.models import Article, PriceHistory
from ...core.price_engine import PriceEngine
from ..components.data_table import DataTable
from ..components.dialogs import ArticleDialog, PriceHistoryDialog

# Couleurs thème
_DANGER = QColor("#ff5252")
_WARNING = QColor("#ffab40")
_SUCCESS = QColor("#69f0ae")
_VIOLET = QColor("#7c4dff")
_DIM = QColor("#888888")


class InventoryView(QWidget):
    """Écran Inventaire — liste, ajout, édition, suppression, historique prix."""

    COLUMNS = [
        "ID", "Référence", "Nom", "Catégorie", "Emplacement",
        "Qté", "Qté min", "Prix bas", "Prix moy.", "Prix haut",
        "Mode", "Confiance", "Fournisseur",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = PriceEngine()
        self._articles: list[Article] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Statistiques rapides ──
        stats_box = QGroupBox()
        stats_grid = QGridLayout(stats_box)
        self.stat_labels: dict[str, QLabel] = {}
        for i, (key, title) in enumerate([
            ("total_articles", "Références"),
            ("total_quantity", "Quantité totale"),
            ("total_value", "Valeur estimée"),
            ("low_stock_count", "Stock faible"),
        ]):
            val_lbl = QLabel("0")
            val_lbl.setObjectName("statValue")
            val_lbl.setAlignment(Qt.AlignCenter)
            title_lbl = QLabel(title)
            title_lbl.setObjectName("statLabel")
            title_lbl.setAlignment(Qt.AlignCenter)
            stats_grid.addWidget(val_lbl, 0, i)
            stats_grid.addWidget(title_lbl, 1, i)
            self.stat_labels[key] = val_lbl
        layout.addWidget(stats_box)

        # ── Titre + boutons ──
        top_bar = QHBoxLayout()
        title = QLabel("Inventaire")
        title.setObjectName("sectionTitle")
        top_bar.addWidget(title)
        top_bar.addStretch()

        btn_add = QPushButton("  Ajouter")
        btn_add.clicked.connect(self._add)
        top_bar.addWidget(btn_add)

        btn_edit = QPushButton("  Modifier")
        btn_edit.setObjectName("btnSecondary")
        btn_edit.clicked.connect(self._edit)
        top_bar.addWidget(btn_edit)

        btn_hist = QPushButton("  Historique prix")
        btn_hist.setObjectName("btnFlat")
        btn_hist.clicked.connect(self._add_history)
        top_bar.addWidget(btn_hist)

        btn_recalc = QPushButton("  Recalculer prix")
        btn_recalc.setObjectName("btnFlat")
        btn_recalc.clicked.connect(self._recalculate_all)
        top_bar.addWidget(btn_recalc)

        btn_del = QPushButton("  Supprimer")
        btn_del.setObjectName("btnDanger")
        btn_del.clicked.connect(self._delete)
        top_bar.addWidget(btn_del)

        layout.addLayout(top_bar)

        # ── Filtres rapides ──
        filters_bar = QHBoxLayout()
        filters_bar.setSpacing(6)

        lbl_filter = QLabel("Filtres :")
        lbl_filter.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        filters_bar.addWidget(lbl_filter)

        self._quick_filter = "tous"

        self.btn_all = QPushButton("Tous")
        self.btn_all.setObjectName("btnQuickFilter")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self._set_quick_filter("tous"))
        filters_bar.addWidget(self.btn_all)

        self.btn_low_stock = QPushButton("⚠ Stock bas")
        self.btn_low_stock.setObjectName("btnQuickFilter")
        self.btn_low_stock.setCheckable(True)
        self.btn_low_stock.clicked.connect(lambda: self._set_quick_filter("stock_bas"))
        filters_bar.addWidget(self.btn_low_stock)

        self.btn_inconsistent = QPushButton("⚡ Prix incohérent")
        self.btn_inconsistent.setObjectName("btnQuickFilter")
        self.btn_inconsistent.setCheckable(True)
        self.btn_inconsistent.clicked.connect(lambda: self._set_quick_filter("incoherent"))
        filters_bar.addWidget(self.btn_inconsistent)

        self.btn_no_price = QPushButton("∅ Sans prix")
        self.btn_no_price.setObjectName("btnQuickFilter")
        self.btn_no_price.setCheckable(True)
        self.btn_no_price.clicked.connect(lambda: self._set_quick_filter("sans_prix"))
        filters_bar.addWidget(self.btn_no_price)

        filters_bar.addStretch()

        # Filtre emplacement
        self.loc_filter = QComboBox()
        self.loc_filter.addItem("Tous emplacements")
        for l in db.get_locations():
            self.loc_filter.addItem(l.name)
        self.loc_filter.currentTextChanged.connect(lambda _: self.refresh())
        filters_bar.addWidget(self.loc_filter)

        # Filtre fournisseur
        self.sup_filter = QComboBox()
        self.sup_filter.addItem("Tous fournisseurs")
        for s in db.get_suppliers():
            self.sup_filter.addItem(s.name)
        self.sup_filter.currentTextChanged.connect(lambda _: self.refresh())
        filters_bar.addWidget(self.sup_filter)

        layout.addLayout(filters_bar)

        # ── Tableau ──
        categories = [c.name for c in db.get_categories()]
        self.table = DataTable(
            self.COLUMNS, self,
            filter_column=3,
            filter_items=categories,
            color_function=self._row_color,
        )
        self.table.row_double_clicked.connect(self._edit)
        layout.addWidget(self.table)

        self.refresh()

    # ─── Filtres rapides ────────────────────────────
    def _set_quick_filter(self, mode: str):
        self._quick_filter = mode
        for btn in (self.btn_all, self.btn_low_stock, self.btn_inconsistent, self.btn_no_price):
            btn.setChecked(False)
        if mode == "tous":
            self.btn_all.setChecked(True)
        elif mode == "stock_bas":
            self.btn_low_stock.setChecked(True)
        elif mode == "incoherent":
            self.btn_inconsistent.setChecked(True)
        elif mode == "sans_prix":
            self.btn_no_price.setChecked(True)
        self.refresh()

    # ─── Coloration dynamique ──────────────────────
    def _row_color(self, row: list, col: int) -> QColor | None:
        """Retourne une couleur de texte pour la cellule (row, col)."""
        # Col 5=Qté, Col 6=Qté min
        try:
            qty = float(row[5]) if row[5] else 0
            qty_min = float(row[6]) if row[6] else 0
        except (ValueError, IndexError):
            qty, qty_min = 0, 0

        # Stock bas → rouge sur colonne Qté
        if col == 5 and qty_min > 0 and qty <= qty_min:
            return _DANGER

        # Confiance (col 14)
        if col == 14:
            conf = str(row[14]).lower()
            if conf == "fort":
                return _SUCCESS
            elif conf == "moyen":
                return _WARNING
            elif conf == "faible":
                return _DANGER

        # Totaux (col 10,11,12) — violet
        if col in (10, 11, 12):
            return _VIOLET

        return None

    # ─── Rafraîchir ──────────────────────────────────
    def refresh(self):
        self._articles = db.get_articles()

        # Filtres rapides
        loc_text = self.loc_filter.currentText()
        sup_text = self.sup_filter.currentText()

        filtered = []
        for a in self._articles:
            # Filtre emplacement
            if loc_text != "Tous emplacements" and a.location_name != loc_text:
                continue
            # Filtre fournisseur
            if sup_text != "Tous fournisseurs" and a.supplier_name != sup_text:
                continue
            # Filtres rapides
            if self._quick_filter == "stock_bas" and not a.is_low_stock:
                continue
            if self._quick_filter == "incoherent" and not a.is_price_inconsistent:
                continue
            if self._quick_filter == "sans_prix" and a.price_avg > 0:
                continue
            filtered.append(a)

        rows = []
        for a in filtered:
            rows.append([
                a.id, a.reference, a.name, a.category_name, a.location_name,
                a.quantity, a.quantity_min,
                f"{a.price_low:.2f}", f"{a.price_avg:.2f}", f"{a.price_high:.2f}",
                f"{a.total_low:.2f}", f"{a.total_avg:.2f}", f"{a.total_high:.2f}",
                a.price_mode, a.confidence, a.supplier_name,
            ])
        self.table.set_data(rows)
        self._refresh_stats()

    def _refresh_stats(self):
        stats = db.get_stats()
        for key, lbl in self.stat_labels.items():
            val = stats.get(key, 0)
            if key == "total_value":
                lbl.setText(f"{val:,.2f} €")
            else:
                lbl.setText(str(val))

    # ─── Ajouter ─────────────────────────────────────
    def _add(self):
        dlg = ArticleDialog(
            self,
            categories=db.get_categories(),
            locations=db.get_locations(),
            suppliers=db.get_suppliers(),
        )
        if dlg.exec() == ArticleDialog.Accepted:
            article = dlg.get_article()
            article = self.engine.apply_price(article)
            db.add_article(article)
            self.refresh()

    # ─── Modifier ────────────────────────────────────
    def _edit(self, row_idx=None):
        article = self._selected_article()
        if not article:
            return
        dlg = ArticleDialog(
            self, article=article,
            categories=db.get_categories(),
            locations=db.get_locations(),
            suppliers=db.get_suppliers(),
        )
        if dlg.exec() == ArticleDialog.Accepted:
            updated = dlg.get_article()
            updated = self.engine.apply_price(updated)
            db.update_article(updated)
            self.refresh()

    # ─── Supprimer ───────────────────────────────────
    def _delete(self):
        article = self._selected_article()
        if not article:
            return
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer « {article.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_article(article.id)
            self.refresh()

    # ─── Ajouter historique de prix ──────────────────
    def _add_history(self):
        article = self._selected_article()
        if not article:
            return
        dlg = PriceHistoryDialog(self, article.name, db.get_suppliers())
        if dlg.exec() == PriceHistoryDialog.Accepted:
            vals = dlg.get_values()
            h = PriceHistory(
                article_id=article.id,
                price=vals["price"],
                quantity=vals["quantity"],
                supplier_id=vals["supplier_id"],
                notes=vals["notes"],
            )
            db.add_price_history(h)
            # Recalculer le prix
            article = self.engine.apply_price(article)
            db.update_article(article)
            self.refresh()

    # ─── Recalculer tous les prix ────────────────────
    def _recalculate_all(self):
        for a in self._articles:
            a = self.engine.apply_price(a)
            db.update_article(a)
        self.refresh()
        QMessageBox.information(self, "Terminé",
                                f"Prix recalculés pour {len(self._articles)} articles.")

    # ─── Sélection ───────────────────────────────────
    def _selected_article(self) -> Article | None:
        data = self.table.selected_row_data()
        if data is None:
            QMessageBox.warning(self, "Sélection", "Veuillez sélectionner un article.")
            return None
        art_id = data[0]
        return next((a for a in self._articles if a.id == art_id), None)
