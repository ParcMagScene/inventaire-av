"""
price_settings_view.py — Paramétrage du moteur de prix.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QMessageBox,
    QComboBox, QScrollArea,
)

from ...core import database as db


class PriceSettingsView(QWidget):
    """Configuration des règles du moteur de prix intelligent."""

    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Paramètres du moteur de prix")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ── Fourchettes ──
        grp1 = QGroupBox("Fourchettes de prix")
        form1 = QFormLayout(grp1)

        self.low_factor = QDoubleSpinBox()
        self.low_factor.setRange(0.01, 1.0)
        self.low_factor.setDecimals(2)
        self.low_factor.setSingleStep(0.05)
        form1.addRow("Facteur prix bas :", self.low_factor)

        self.high_factor = QDoubleSpinBox()
        self.high_factor.setRange(1.0, 5.0)
        self.high_factor.setDecimals(2)
        self.high_factor.setSingleStep(0.05)
        form1.addRow("Facteur prix haut :", self.high_factor)

        layout.addWidget(grp1)

        # ── Historique ──
        grp2 = QGroupBox("Historique")
        form2 = QFormLayout(grp2)

        self.decay_days = QSpinBox()
        self.decay_days.setRange(1, 3650)
        form2.addRow("Décroissance temporelle (jours) :", self.decay_days)

        self.outlier_sigma = QDoubleSpinBox()
        self.outlier_sigma.setRange(0.5, 5.0)
        self.outlier_sigma.setDecimals(1)
        self.outlier_sigma.setSingleStep(0.5)
        form2.addRow("Seuil aberration (σ) :", self.outlier_sigma)

        self.min_entries = QSpinBox()
        self.min_entries.setRange(1, 100)
        form2.addRow("Entrées min. pour confiance :", self.min_entries)

        layout.addWidget(grp2)

        # ── Pondérations sources ──
        grp3 = QGroupBox("Pondération des sources")
        form3 = QFormLayout(grp3)

        self.w_reference = QDoubleSpinBox()
        self.w_reference.setRange(0, 2)
        self.w_reference.setDecimals(2)
        form3.addRow("Référence :", self.w_reference)

        self.w_history = QDoubleSpinBox()
        self.w_history.setRange(0, 2)
        self.w_history.setDecimals(2)
        form3.addRow("Historique :", self.w_history)

        self.w_category = QDoubleSpinBox()
        self.w_category.setRange(0, 2)
        self.w_category.setDecimals(2)
        form3.addRow("Catégorie :", self.w_category)

        self.w_supplier = QDoubleSpinBox()
        self.w_supplier.setRange(0, 2)
        self.w_supplier.setDecimals(2)
        form3.addRow("Fournisseur :", self.w_supplier)

        self.w_default = QDoubleSpinBox()
        self.w_default.setRange(0, 2)
        self.w_default.setDecimals(2)
        form3.addRow("Défaut :", self.w_default)

        layout.addWidget(grp3)

        # ── Profils fournisseurs ──
        grp4 = QGroupBox("Profils fournisseurs (facteur multiplicateur)")
        form4 = QFormLayout(grp4)

        self.sup_eco = QDoubleSpinBox()
        self.sup_eco.setRange(0.1, 3.0)
        self.sup_eco.setDecimals(2)
        form4.addRow("Économique :", self.sup_eco)

        self.sup_moyen = QDoubleSpinBox()
        self.sup_moyen.setRange(0.1, 3.0)
        self.sup_moyen.setDecimals(2)
        form4.addRow("Moyen :", self.sup_moyen)

        self.sup_cher = QDoubleSpinBox()
        self.sup_cher.setRange(0.1, 3.0)
        self.sup_cher.setDecimals(2)
        form4.addRow("Cher :", self.sup_cher)

        layout.addWidget(grp4)

        # ── Bouton sauvegarder ──
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        btn_save = QPushButton("  Sauvegarder")
        btn_save.setMinimumWidth(180)
        btn_save.clicked.connect(self._save)
        btn_bar.addWidget(btn_save)
        layout.addLayout(btn_bar)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._load()

    def _load(self):
        rules = db.get_price_rules()
        self.low_factor.setValue(rules.get("price_low_factor", 0.80))
        self.high_factor.setValue(rules.get("price_high_factor", 1.25))
        self.decay_days.setValue(int(rules.get("history_decay_days", 180)))
        self.outlier_sigma.setValue(rules.get("outlier_sigma", 2.0))
        self.min_entries.setValue(int(rules.get("min_history_entries", 3)))
        self.w_reference.setValue(rules.get("weight_reference", 1.0))
        self.w_history.setValue(rules.get("weight_history", 0.8))
        self.w_category.setValue(rules.get("weight_category", 0.5))
        self.w_supplier.setValue(rules.get("weight_supplier", 0.6))
        self.w_default.setValue(rules.get("weight_default", 0.2))
        self.sup_eco.setValue(rules.get("supplier_economique", 0.85))
        self.sup_moyen.setValue(rules.get("supplier_moyen", 1.0))
        self.sup_cher.setValue(rules.get("supplier_cher", 1.2))

    def _save(self):
        pairs = [
            ("price_low_factor", self.low_factor.value()),
            ("price_high_factor", self.high_factor.value()),
            ("history_decay_days", float(self.decay_days.value())),
            ("outlier_sigma", self.outlier_sigma.value()),
            ("min_history_entries", float(self.min_entries.value())),
            ("weight_reference", self.w_reference.value()),
            ("weight_history", self.w_history.value()),
            ("weight_category", self.w_category.value()),
            ("weight_supplier", self.w_supplier.value()),
            ("weight_default", self.w_default.value()),
            ("supplier_economique", self.sup_eco.value()),
            ("supplier_moyen", self.sup_moyen.value()),
            ("supplier_cher", self.sup_cher.value()),
        ]
        for key, val in pairs:
            db.set_price_rule(key, val, key)
        QMessageBox.information(self, "Sauvegardé", "Paramètres de prix enregistrés.")

    def refresh(self):
        self._load()
