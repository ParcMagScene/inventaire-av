"""
inventory_view.py — Vue principale de l'inventaire des articles.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QGroupBox, QGridLayout,
)

from ...core import database as db
from ...core.models import Article, PriceHistory
from ...core.price_engine import PriceEngine
from ..components.data_table import DataTable
from ..components.dialogs import ArticleDialog, PriceHistoryDialog


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

        # ── Tableau ──
        categories = [c.name for c in db.get_categories()]
        self.table = DataTable(
            self.COLUMNS, self,
            filter_column=3,
            filter_items=categories,
        )
        self.table.row_double_clicked.connect(self._edit)
        layout.addWidget(self.table)

        self.refresh()

    # ─── Rafraîchir ──────────────────────────────────
    def refresh(self):
        self._articles = db.get_articles()
        rows = []
        for a in self._articles:
            rows.append([
                a.id, a.reference, a.name, a.category_name, a.location_name,
                a.quantity, a.quantity_min,
                f"{a.price_low:.2f}", f"{a.price_avg:.2f}", f"{a.price_high:.2f}",
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
