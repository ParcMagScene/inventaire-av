"""
dialogs.py — Dialogues de saisie pour les différentes entités.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPushButton,
    QLabel, QDialogButtonBox, QMessageBox, QGroupBox,
)

from ...core.models import Article, Category, Location, Supplier


# ─── Utilitaire ──────────────────────────────────────────
def _form_row(form: QFormLayout, label: str, widget):
    form.addRow(QLabel(label), widget)
    return widget


# ═════════════════════════════════════════════════════════
#  Dialog Article
# ═════════════════════════════════════════════════════════
class ArticleDialog(QDialog):
    def __init__(self, parent=None, article: Article | None = None,
                 categories=None, locations=None, suppliers=None):
        super().__init__(parent)
        self.setWindowTitle("Modifier l'article" if article else "Nouvel article")
        self.setMinimumWidth(520)
        self.article = article or Article()
        self._categories = categories or []
        self._locations = locations or []
        self._suppliers = suppliers or []

        layout = QVBoxLayout(self)

        # ── Infos générales ──
        grp = QGroupBox("Informations générales")
        form = QFormLayout(grp)

        self.ref_input = _form_row(form, "Référence :", QLineEdit(self.article.reference))
        self.name_input = _form_row(form, "Nom :", QLineEdit(self.article.name))
        self.desc_input = _form_row(form, "Description :", QLineEdit(self.article.description))

        self.cat_combo = QComboBox()
        self.cat_combo.addItem("— Aucune —", None)
        for c in self._categories:
            self.cat_combo.addItem(c.name, c.id)
        if self.article.category_id:
            idx = self.cat_combo.findData(self.article.category_id)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
        _form_row(form, "Catégorie :", self.cat_combo)

        self.loc_combo = QComboBox()
        self.loc_combo.addItem("— Aucun —", None)
        for l in self._locations:
            self.loc_combo.addItem(l.name, l.id)
        if self.article.location_id:
            idx = self.loc_combo.findData(self.article.location_id)
            if idx >= 0:
                self.loc_combo.setCurrentIndex(idx)
        _form_row(form, "Emplacement :", self.loc_combo)

        self.sup_combo = QComboBox()
        self.sup_combo.addItem("— Aucun —", None)
        for s in self._suppliers:
            self.sup_combo.addItem(s.name, s.id)
        if self.article.supplier_id:
            idx = self.sup_combo.findData(self.article.supplier_id)
            if idx >= 0:
                self.sup_combo.setCurrentIndex(idx)
        _form_row(form, "Fournisseur :", self.sup_combo)

        layout.addWidget(grp)

        # ── Quantités ──
        grp2 = QGroupBox("Stock")
        form2 = QFormLayout(grp2)
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 999999)
        self.qty_spin.setValue(self.article.quantity)
        _form_row(form2, "Quantité :", self.qty_spin)

        self.qty_min_spin = QSpinBox()
        self.qty_min_spin.setRange(0, 999999)
        self.qty_min_spin.setValue(self.article.quantity_min)
        _form_row(form2, "Seuil minimum :", self.qty_min_spin)
        layout.addWidget(grp2)

        # ── Prix ──
        grp3 = QGroupBox("Prix")
        form3 = QFormLayout(grp3)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["automatique", "manuel", "mixte"])
        self.mode_combo.setCurrentText(self.article.price_mode)
        self.mode_combo.currentTextChanged.connect(self._on_mode_change)
        _form_row(form3, "Mode de prix :", self.mode_combo)

        self.manual_price = QDoubleSpinBox()
        self.manual_price.setRange(0, 999999)
        self.manual_price.setDecimals(2)
        self.manual_price.setSuffix(" €")
        self.manual_price.setValue(self.article.price_manual or 0)
        _form_row(form3, "Prix manuel :", self.manual_price)

        self.manual_low = QDoubleSpinBox()
        self.manual_low.setRange(0, 999999)
        self.manual_low.setDecimals(2)
        self.manual_low.setSuffix(" €")
        self.manual_low.setValue(self.article.price_manual_low or 0)
        _form_row(form3, "Prix bas (manuel) :", self.manual_low)

        self.manual_high = QDoubleSpinBox()
        self.manual_high.setRange(0, 999999)
        self.manual_high.setDecimals(2)
        self.manual_high.setSuffix(" €")
        self.manual_high.setValue(self.article.price_manual_high or 0)
        _form_row(form3, "Prix haut (manuel) :", self.manual_high)

        layout.addWidget(grp3)

        # ── Notes ──
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes…")
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlainText(self.article.notes)
        layout.addWidget(self.notes_input)

        # ── Boutons ──
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._on_mode_change(self.mode_combo.currentText())

    def _on_mode_change(self, mode: str):
        manual = mode == "manuel"
        self.manual_price.setEnabled(manual)
        self.manual_low.setEnabled(manual)
        self.manual_high.setEnabled(manual)

    def _validate(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        self.article.reference = self.ref_input.text().strip()
        self.article.name = self.name_input.text().strip()
        self.article.description = self.desc_input.text().strip()
        self.article.category_id = self.cat_combo.currentData()
        self.article.location_id = self.loc_combo.currentData()
        self.article.supplier_id = self.sup_combo.currentData()
        self.article.quantity = self.qty_spin.value()
        self.article.quantity_min = self.qty_min_spin.value()
        self.article.price_mode = self.mode_combo.currentText()
        self.article.price_manual = self.manual_price.value() or None
        self.article.price_manual_low = self.manual_low.value() or None
        self.article.price_manual_high = self.manual_high.value() or None
        self.article.notes = self.notes_input.toPlainText()
        self.accept()

    def get_article(self) -> Article:
        return self.article


# ═════════════════════════════════════════════════════════
#  Dialog Catégorie
# ═════════════════════════════════════════════════════════
class CategoryDialog(QDialog):
    def __init__(self, parent=None, category: Category | None = None):
        super().__init__(parent)
        self.setWindowTitle("Modifier la catégorie" if category else "Nouvelle catégorie")
        self.setMinimumWidth(400)
        self.category = category or Category()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = _form_row(form, "Nom :", QLineEdit(self.category.name))
        self.desc_input = _form_row(form, "Description :", QLineEdit(self.category.description))
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix(" €")
        self.price_input.setValue(self.category.default_price)
        _form_row(form, "Prix par défaut :", self.price_input)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        self.category.name = self.name_input.text().strip()
        self.category.description = self.desc_input.text().strip()
        self.category.default_price = self.price_input.value()
        self.accept()

    def get_category(self) -> Category:
        return self.category


# ═════════════════════════════════════════════════════════
#  Dialog Emplacement
# ═════════════════════════════════════════════════════════
class LocationDialog(QDialog):
    def __init__(self, parent=None, location: Location | None = None):
        super().__init__(parent)
        self.setWindowTitle("Modifier l'emplacement" if location else "Nouvel emplacement")
        self.setMinimumWidth(400)
        self.location = location or Location()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = _form_row(form, "Nom :", QLineEdit(self.location.name))
        self.desc_input = _form_row(form, "Description :", QLineEdit(self.location.description))
        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        self.location.name = self.name_input.text().strip()
        self.location.description = self.desc_input.text().strip()
        self.accept()

    def get_location(self) -> Location:
        return self.location


# ═════════════════════════════════════════════════════════
#  Dialog Fournisseur
# ═════════════════════════════════════════════════════════
class SupplierDialog(QDialog):
    def __init__(self, parent=None, supplier: Supplier | None = None):
        super().__init__(parent)
        self.setWindowTitle("Modifier le fournisseur" if supplier else "Nouveau fournisseur")
        self.setMinimumWidth(450)
        self.supplier = supplier or Supplier()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = _form_row(form, "Nom :", QLineEdit(self.supplier.name))
        self.contact_input = _form_row(form, "Contact :", QLineEdit(self.supplier.contact))
        self.email_input = _form_row(form, "Email :", QLineEdit(self.supplier.email))
        self.phone_input = _form_row(form, "Téléphone :", QLineEdit(self.supplier.phone))

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["economique", "moyen", "cher"])
        self.profile_combo.setCurrentText(self.supplier.profile)
        _form_row(form, "Profil prix :", self.profile_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        self.notes_input.setPlainText(self.supplier.notes)
        _form_row(form, "Notes :", self.notes_input)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        self.supplier.name = self.name_input.text().strip()
        self.supplier.contact = self.contact_input.text().strip()
        self.supplier.email = self.email_input.text().strip()
        self.supplier.phone = self.phone_input.text().strip()
        self.supplier.profile = self.profile_combo.currentText()
        self.supplier.notes = self.notes_input.toPlainText()
        self.accept()

    def get_supplier(self) -> Supplier:
        return self.supplier


# ═════════════════════════════════════════════════════════
#  Dialog Historique de prix
# ═════════════════════════════════════════════════════════
class PriceHistoryDialog(QDialog):
    def __init__(self, parent=None, article_name: str = "", suppliers=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ajouter un prix – {article_name}")
        self.setMinimumWidth(400)
        self._suppliers = suppliers or []

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 999999)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix(" €")
        _form_row(form, "Prix unitaire :", self.price_input)

        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 999999)
        self.qty_input.setValue(1)
        _form_row(form, "Quantité :", self.qty_input)

        self.sup_combo = QComboBox()
        self.sup_combo.addItem("— Aucun —", None)
        for s in self._suppliers:
            self.sup_combo.addItem(s.name, s.id)
        _form_row(form, "Fournisseur :", self.sup_combo)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Note optionnelle…")
        _form_row(form, "Notes :", self.notes_input)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_values(self) -> dict:
        return {
            "price": self.price_input.value(),
            "quantity": self.qty_input.value(),
            "supplier_id": self.sup_combo.currentData(),
            "notes": self.notes_input.text(),
        }
