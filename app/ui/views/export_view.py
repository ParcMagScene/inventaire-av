"""
export_view.py — Export PDF avec filtres.
"""
import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QPushButton, QLabel, QFileDialog, QMessageBox,
)

from ...core import database as db
from ...core.pdf_exporter import PDFExporter


class ExportView(QWidget):
    """Écran d'export PDF."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Export PDF")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Générez un rapport PDF complet de votre inventaire, avec totaux "
            "par catégorie, par emplacement et totaux globaux."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── Filtres ──
        grp = QGroupBox("Filtres (optionnels)")
        form = QFormLayout(grp)

        self.cat_combo = QComboBox()
        self.cat_combo.addItem("Toutes les catégories", None)
        for c in db.get_categories():
            self.cat_combo.addItem(c.name, c.id)
        form.addRow("Catégorie :", self.cat_combo)

        self.loc_combo = QComboBox()
        self.loc_combo.addItem("Tous les emplacements", None)
        for l in db.get_locations():
            self.loc_combo.addItem(l.name, l.id)
        form.addRow("Emplacement :", self.loc_combo)

        layout.addWidget(grp)

        # ── Bouton export ──
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        btn_export = QPushButton("  Exporter en PDF")
        btn_export.setMinimumWidth(200)
        btn_export.setMinimumHeight(44)
        btn_export.clicked.connect(self._export)
        btn_bar.addWidget(btn_export)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        # ── Status ──
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _export(self):
        date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        default_name = f"inventaire_{date_str}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le PDF", default_name,
            "Fichiers PDF (*.pdf)",
        )
        if not path:
            return

        try:
            exporter = PDFExporter()
            exporter.export(
                path,
                category_id=self.cat_combo.currentData(),
                location_id=self.loc_combo.currentData(),
            )
            self.status_label.setText(f"✅  PDF exporté : {path}")
            QMessageBox.information(self, "Succès", f"PDF exporté avec succès :\n{path}")
        except Exception as e:
            self.status_label.setText(f"❌  Erreur : {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export :\n{e}")

    def refresh(self):
        # Recharger les combos
        self.cat_combo.clear()
        self.cat_combo.addItem("Toutes les catégories", None)
        for c in db.get_categories():
            self.cat_combo.addItem(c.name, c.id)

        self.loc_combo.clear()
        self.loc_combo.addItem("Tous les emplacements", None)
        for l in db.get_locations():
            self.loc_combo.addItem(l.name, l.id)
