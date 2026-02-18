"""
suppliers_view.py — Gestion des fournisseurs.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
)

from ...core import database as db
from ...core.models import Supplier
from ..components.data_table import DataTable
from ..components.dialogs import SupplierDialog


class SuppliersView(QWidget):
    COLUMNS = ["ID", "Nom", "Contact", "Email", "Téléphone", "Profil"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppliers: list[Supplier] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Fournisseurs")
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
        self._suppliers = db.get_suppliers()
        rows = [[s.id, s.name, s.contact, s.email, s.phone, s.profile]
                for s in self._suppliers]
        self.table.set_data(rows)

    def _add(self):
        dlg = SupplierDialog(self)
        if dlg.exec() == SupplierDialog.Accepted:
            db.add_supplier(dlg.get_supplier())
            self.refresh()

    def _edit(self, _=None):
        sup = self._selected()
        if not sup:
            return
        dlg = SupplierDialog(self, supplier=sup)
        if dlg.exec() == SupplierDialog.Accepted:
            db.update_supplier(dlg.get_supplier())
            self.refresh()

    def _delete(self):
        sup = self._selected()
        if not sup:
            return
        if QMessageBox.question(
            self, "Confirmer", f"Supprimer « {sup.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            db.delete_supplier(sup.id)
            self.refresh()

    def _selected(self) -> Supplier | None:
        data = self.table.selected_row_data()
        if data is None:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un fournisseur.")
            return None
        sid = data[0]
        return next((s for s in self._suppliers if s.id == sid), None)
