"""
categories_view.py — Gestion des catégories.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
)

from ...core import database as db
from ...core.models import Category
from ..components.data_table import DataTable
from ..components.dialogs import CategoryDialog


class CategoriesView(QWidget):
    COLUMNS = ["ID", "Nom", "Description", "Prix par défaut"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories: list[Category] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Catégories")
        title.setObjectName("sectionTitle")
        top.addWidget(title)
        top.addStretch()

        btn_add = QPushButton("  Ajouter")
        btn_add.clicked.connect(self._add)
        top.addWidget(btn_add)

        btn_edit = QPushButton("  Modifier")
        btn_edit.setObjectName("btnSecondary")
        btn_edit.clicked.connect(self._edit)
        top.addWidget(btn_edit)

        btn_del = QPushButton("  Supprimer")
        btn_del.setObjectName("btnDanger")
        btn_del.clicked.connect(self._delete)
        top.addWidget(btn_del)

        layout.addLayout(top)

        self.table = DataTable(self.COLUMNS, self)
        self.table.row_double_clicked.connect(self._edit)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        self._categories = db.get_categories()
        rows = [[c.id, c.name, c.description, f"{c.default_price:.2f} €"]
                for c in self._categories]
        self.table.set_data(rows)

    def _add(self):
        dlg = CategoryDialog(self)
        if dlg.exec() == CategoryDialog.Accepted:
            db.add_category(dlg.get_category())
            self.refresh()

    def _edit(self, _=None):
        cat = self._selected()
        if not cat:
            return
        dlg = CategoryDialog(self, category=cat)
        if dlg.exec() == CategoryDialog.Accepted:
            db.update_category(dlg.get_category())
            self.refresh()

    def _delete(self):
        cat = self._selected()
        if not cat:
            return
        if QMessageBox.question(
            self, "Confirmer", f"Supprimer « {cat.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            db.delete_category(cat.id)
            self.refresh()

    def _selected(self) -> Category | None:
        data = self.table.selected_row_data()
        if data is None:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une catégorie.")
            return None
        cid = data[0]
        return next((c for c in self._categories if c.id == cid), None)
