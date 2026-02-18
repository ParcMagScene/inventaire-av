"""
locations_view.py — Gestion des emplacements.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
)

from ...core import database as db
from ...core.models import Location
from ..components.data_table import DataTable
from ..components.dialogs import LocationDialog


class LocationsView(QWidget):
    COLUMNS = ["ID", "Nom", "Description"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locations: list[Location] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Emplacements")
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
        self._locations = db.get_locations()
        rows = [[l.id, l.name, l.description] for l in self._locations]
        self.table.set_data(rows)

    def _add(self):
        dlg = LocationDialog(self)
        if dlg.exec() == LocationDialog.Accepted:
            db.add_location(dlg.get_location())
            self.refresh()

    def _edit(self, _=None):
        loc = self._selected()
        if not loc:
            return
        dlg = LocationDialog(self, location=loc)
        if dlg.exec() == LocationDialog.Accepted:
            db.update_location(dlg.get_location())
            self.refresh()

    def _delete(self):
        loc = self._selected()
        if not loc:
            return
        if QMessageBox.question(
            self, "Confirmer", f"Supprimer « {loc.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            db.delete_location(loc.id)
            self.refresh()

    def _selected(self) -> Location | None:
        data = self.table.selected_row_data()
        if data is None:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un emplacement.")
            return None
        lid = data[0]
        return next((l for l in self._locations if l.id == lid), None)
