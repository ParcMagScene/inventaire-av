"""
dialogs.py — Dialogues de saisie pour les différentes entités.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPushButton,
    QLabel, QDialogButtonBox, QMessageBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter, QListWidget, QListWidgetItem, QScrollArea, QWidget,
)

from ...core.models import Article, Category, Location, Supplier
from ...core import database as db


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


# ═════════════════════════════════════════════════════════
#  Dialog Ajout structuré par lots (Zone / Catégorie / Type)
# ═════════════════════════════════════════════════════════
class StructuredAddDialog(QDialog):
    """Ajout d'équipements par lots avec recherche et création de types."""

    _BATCH_COLS = ["Nom", "Référence", "Description", "Qté", "Qté min",
                   "Mode prix", "Prix", "Notes"]

    def __init__(self, parent=None, categories=None, locations=None, suppliers=None):
        super().__init__(parent)
        self.setWindowTitle("Ajout structuré par lots")
        self.setMinimumSize(920, 750)
        self._categories = categories or []
        self._locations = locations or []
        self._suppliers = suppliers or []
        self._tool_categories = db.get_tool_categories()
        self._all_tool_types: list = db.get_tool_types()   # tous les types (pour recherche)
        self._tool_types: list = []                         # types filtrés par catégorie
        self._batch: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 8)

        # ── Scroll Area pour éviter l'écrasement ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(12, 12, 12, 4)
        root.setSpacing(10)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        # ══════════════ Recherche rapide ══════════════
        grp_search = QGroupBox("🔍 Recherche dans le catalogue")
        search_layout = QVBoxLayout(grp_search)
        search_layout.setSpacing(4)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setMinimumHeight(32)
        self.search_input.setPlaceholderText("Tapez pour chercher un outil (ex: tournevis PH2, clé 17, embout torx…)")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input)

        self.btn_create_type = QPushButton("  ＋ Créer un type  ")
        self.btn_create_type.setMinimumHeight(32)
        self.btn_create_type.setObjectName("btnSecondary")
        self.btn_create_type.setToolTip("Créer un nouveau type d'outil dans le catalogue")
        self.btn_create_type.clicked.connect(self._create_tool_type)
        search_row.addWidget(self.btn_create_type)
        search_layout.addLayout(search_row)

        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(120)
        self.search_results.setVisible(False)
        self.search_results.itemClicked.connect(self._on_search_result_clicked)
        search_layout.addWidget(self.search_results)

        self.search_count_label = QLabel("")
        self.search_count_label.setStyleSheet("color: #888; font-style: italic;")
        search_layout.addWidget(self.search_count_label)

        root.addWidget(grp_search)

        # ══════════════ Contexte persistant ══════════════
        grp_ctx = QGroupBox("Contexte (commun à tous les articles du lot)")
        form_ctx = QFormLayout(grp_ctx)
        form_ctx.setSpacing(6)

        self.loc_combo = QComboBox()
        self.loc_combo.setMinimumHeight(28)
        self.loc_combo.addItem("— Aucun —", None)
        for loc in self._locations:
            self.loc_combo.addItem(loc.name, loc.id)
        _form_row(form_ctx, "Emplacement :", self.loc_combo)

        self.cat_combo = QComboBox()
        self.cat_combo.setMinimumHeight(28)
        self.cat_combo.addItem("— Aucune —", None)
        for c in self._categories:
            self.cat_combo.addItem(c.name, c.id)
        _form_row(form_ctx, "Catégorie inventaire :", self.cat_combo)

        self.sup_combo = QComboBox()
        self.sup_combo.setMinimumHeight(28)
        self.sup_combo.addItem("— Aucun —", None)
        for s in self._suppliers:
            self.sup_combo.addItem(s.name, s.id)
        _form_row(form_ctx, "Fournisseur :", self.sup_combo)

        ctx_tool_row = QHBoxLayout()
        self.tool_cat_combo = QComboBox()
        self.tool_cat_combo.setMinimumHeight(28)
        self.tool_cat_combo.addItem("— Catégorie outillage —", None)
        for tc in self._tool_categories:
            self.tool_cat_combo.addItem(tc.name, tc.id)
        self.tool_cat_combo.currentIndexChanged.connect(self._on_tool_cat_changed)
        ctx_tool_row.addWidget(QLabel("Cat. outillage :"))
        ctx_tool_row.addWidget(self.tool_cat_combo)

        self.tool_type_combo = QComboBox()
        self.tool_type_combo.setMinimumHeight(28)
        self.tool_type_combo.addItem("— Type d'équipement —", None)
        self.tool_type_combo.setEnabled(False)
        self.tool_type_combo.currentIndexChanged.connect(self._on_tool_type_changed)
        ctx_tool_row.addWidget(QLabel("Type :"))
        ctx_tool_row.addWidget(self.tool_type_combo)
        form_ctx.addRow(ctx_tool_row)

        root.addWidget(grp_ctx)

        # ══════════════ Saisie rapide d'un article ══════════════
        grp_item = QGroupBox("Nouvel article")
        item_layout = QVBoxLayout(grp_item)
        item_layout.setSpacing(8)
        form_item = QFormLayout()
        form_item.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(32)
        self.name_input.setPlaceholderText("Ex : Tête plate – Taille 3")
        _form_row(form_item, "Nom :", self.name_input)

        self.ref_input = QLineEdit()
        self.ref_input.setMinimumHeight(32)
        self.ref_input.setPlaceholderText("Référence (optionnel)")
        _form_row(form_item, "Référence :", self.ref_input)

        self.desc_input = QLineEdit()
        self.desc_input.setMinimumHeight(32)
        self.desc_input.setPlaceholderText("Description (optionnel)")
        _form_row(form_item, "Description :", self.desc_input)

        # Ligne 1 : Qté + Seuil min
        row_qty1 = QHBoxLayout()
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimumHeight(32)
        self.qty_spin.setMinimumWidth(80)
        self.qty_spin.setRange(1, 999999)
        self.qty_spin.setValue(1)
        row_qty1.addWidget(QLabel("Qté :"))
        row_qty1.addWidget(self.qty_spin)
        row_qty1.addSpacing(16)

        self.qty_min_spin = QSpinBox()
        self.qty_min_spin.setMinimumHeight(32)
        self.qty_min_spin.setMinimumWidth(80)
        self.qty_min_spin.setRange(0, 999999)
        row_qty1.addWidget(QLabel("Seuil min :"))
        row_qty1.addWidget(self.qty_min_spin)
        row_qty1.addStretch()
        form_item.addRow(row_qty1)

        # Ligne 2 : Mode prix + Prix manuel
        row_qty2 = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumHeight(32)
        self.mode_combo.setMinimumWidth(120)
        self.mode_combo.addItems(["automatique", "manuel", "mixte"])
        row_qty2.addWidget(QLabel("Mode prix :"))
        row_qty2.addWidget(self.mode_combo)
        row_qty2.addSpacing(16)

        self.manual_price = QDoubleSpinBox()
        self.manual_price.setMinimumHeight(32)
        self.manual_price.setMinimumWidth(100)
        self.manual_price.setRange(0, 999999)
        self.manual_price.setDecimals(2)
        self.manual_price.setSuffix(" €")
        self.manual_price.setEnabled(False)
        self.mode_combo.currentTextChanged.connect(
            lambda m: self.manual_price.setEnabled(m == "manuel")
        )
        row_qty2.addWidget(QLabel("Prix :"))
        row_qty2.addWidget(self.manual_price)
        row_qty2.addStretch()
        form_item.addRow(row_qty2)

        self.notes_input = QLineEdit()
        self.notes_input.setMinimumHeight(32)
        self.notes_input.setPlaceholderText("Notes (optionnel)")
        _form_row(form_item, "Notes :", self.notes_input)

        self.price_label = QLabel("Prix suggéré : —")
        self.price_label.setStyleSheet("color: #00bfa5; font-weight: bold;")
        form_item.addRow(self.price_label)

        item_layout.addLayout(form_item)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("  ＋  Ajouter au lot  ")
        self.btn_add.setMinimumHeight(36)
        self.btn_add.setObjectName("btnPrimary")
        self.btn_add.clicked.connect(self._add_to_batch)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_add)
        btn_row.addStretch()
        item_layout.addLayout(btn_row)

        root.addWidget(grp_item)

        # ══════════════ Tableau du lot ══════════════
        grp_batch = QGroupBox("Lot en cours")
        batch_layout = QVBoxLayout(grp_batch)

        self.batch_table = QTableWidget(0, len(self._BATCH_COLS))
        self.batch_table.setHorizontalHeaderLabels(self._BATCH_COLS)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.batch_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.batch_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.batch_table.setMinimumHeight(120)
        self.batch_table.setMaximumHeight(200)
        batch_layout.addWidget(self.batch_table)

        batch_btn_row = QHBoxLayout()
        self.btn_remove = QPushButton("Retirer la sélection")
        self.btn_remove.setObjectName("btnDanger")
        self.btn_remove.clicked.connect(self._remove_selected)
        self.batch_count_label = QLabel("0 article(s) dans le lot")
        self.batch_count_label.setStyleSheet("font-weight: bold;")
        batch_btn_row.addWidget(self.btn_remove)
        batch_btn_row.addStretch()
        batch_btn_row.addWidget(self.batch_count_label)
        batch_layout.addLayout(batch_btn_row)

        root.addWidget(grp_batch)

        # ══════════════ Boutons finaux (hors scroll) ══════════════
        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(12, 4, 12, 0)
        self.btn_validate = QPushButton("  ✓  Valider le lot  ")
        self.btn_validate.setMinimumHeight(36)
        self.btn_validate.setObjectName("btnPrimary")
        self.btn_validate.setEnabled(False)
        self.btn_validate.clicked.connect(self.accept)

        btn_cancel = QPushButton("Annuler")
        btn_cancel.setMinimumHeight(36)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_validate)
        outer.addLayout(btn_box)

    # ─── Recherche dans le catalogue ───
    def _on_search_changed(self, text: str):
        text = text.strip().lower()
        self.search_results.clear()
        if len(text) < 2:
            self.search_results.setVisible(False)
            self.search_count_label.setText("")
            return

        # Découper en mots-clés pour un ET logique
        keywords = text.split()
        matches = []
        cat_names = {tc.id: tc.name for tc in self._tool_categories}

        for tt in self._all_tool_types:
            haystack = f"{tt.name} {tt.description} {cat_names.get(tt.category_id, '')}".lower()
            if all(kw in haystack for kw in keywords):
                matches.append(tt)

        self.search_results.setVisible(bool(matches))
        for tt in matches[:50]:
            cat_label = cat_names.get(tt.category_id, "?")
            item = QListWidgetItem(f"[{cat_label}]  {tt.name}  —  {tt.description}  ({tt.default_price:.2f} €)")
            item.setData(Qt.UserRole, tt)
            self.search_results.addItem(item)

        n = len(matches)
        suffix = f" (affichés : 50/{n})" if n > 50 else ""
        self.search_count_label.setText(f"{n} résultat(s){suffix}")

    def _on_search_result_clicked(self, item: QListWidgetItem):
        """Sélectionner un résultat de recherche → positionne les combos et pré-remplit."""
        tt = item.data(Qt.UserRole)
        if not tt:
            return

        # Positionner la catégorie outillage
        for i in range(self.tool_cat_combo.count()):
            if self.tool_cat_combo.itemData(i) == tt.category_id:
                self.tool_cat_combo.setCurrentIndex(i)
                break

        # Positionner le type (après que _on_tool_cat_changed a rechargé les types)
        for i in range(self.tool_type_combo.count()):
            if self.tool_type_combo.itemData(i) == tt.id:
                self.tool_type_combo.setCurrentIndex(i)
                break

        # Pré-remplir les champs
        self.name_input.setText(tt.name)
        self.desc_input.setText(tt.description)
        if tt.default_ref:
            self.ref_input.setText(tt.default_ref)
        self.price_label.setText(f"Prix suggéré : {tt.default_price:.2f} €")

        # Refermer la recherche
        self.search_results.setVisible(False)
        self.search_input.clear()
        self.search_count_label.setText("")
        self.name_input.setFocus()

    # ─── Création d'un nouveau type ───
    def _create_tool_type(self):
        dlg = _CreateToolTypeDialog(self, self._tool_categories)
        if dlg.exec() == QDialog.Accepted:
            new_tt = dlg.get_tool_type()
            new_id = db.add_tool_type(new_tt)
            new_tt.id = new_id
            # Rafraîchir les caches
            self._all_tool_types = db.get_tool_types()
            # Si la catégorie correspond, rafraîchir le combo type
            if new_tt.category_id == self.tool_cat_combo.currentData():
                self._on_tool_cat_changed(self.tool_cat_combo.currentIndex())
            # Pré-remplir avec le nouveau type
            self.name_input.setText(new_tt.name)
            self.desc_input.setText(new_tt.description)
            if new_tt.default_ref:
                self.ref_input.setText(new_tt.default_ref)
            self.price_label.setText(f"Prix suggéré : {new_tt.default_price:.2f} €")
            # Positionner les combos sur le nouveau type
            for i in range(self.tool_cat_combo.count()):
                if self.tool_cat_combo.itemData(i) == new_tt.category_id:
                    self.tool_cat_combo.setCurrentIndex(i)
                    break
            for i in range(self.tool_type_combo.count()):
                if self.tool_type_combo.itemData(i) == new_id:
                    self.tool_type_combo.setCurrentIndex(i)
                    break

    # ─── Slots catégorie / type outillage ───
    def _on_tool_cat_changed(self, _index: int):
        self.tool_type_combo.clear()
        self.tool_type_combo.addItem("— Type d'équipement —", None)
        cat_id = self.tool_cat_combo.currentData()
        if cat_id:
            self._tool_types = db.get_tool_types(category_id=cat_id)
            for tt in self._tool_types:
                self.tool_type_combo.addItem(tt.name, tt.id)
            self.tool_type_combo.setEnabled(True)
        else:
            self._tool_types = []
            self.tool_type_combo.setEnabled(False)

    def _on_tool_type_changed(self, _index: int):
        type_id = self.tool_type_combo.currentData()
        if type_id:
            tt = next((t for t in self._tool_types if t.id == type_id), None)
            if tt:
                if not self.name_input.text():
                    self.name_input.setText(tt.name)
                if not self.ref_input.text() and tt.default_ref:
                    self.ref_input.setText(tt.default_ref)
                self.price_label.setText(f"Prix suggéré : {tt.default_price:.2f} €")

    # ─── Ajout d'une ligne au lot ───
    def _add_to_batch(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Champ requis", "Le nom est obligatoire.")
            return

        entry = {
            "name": name,
            "reference": self.ref_input.text().strip(),
            "description": self.desc_input.text().strip(),
            "quantity": self.qty_spin.value(),
            "quantity_min": self.qty_min_spin.value(),
            "price_mode": self.mode_combo.currentText(),
            "price_manual": self.manual_price.value() if self.mode_combo.currentText() == "manuel" else None,
            "notes": self.notes_input.text().strip(),
            "tool_type_id": self.tool_type_combo.currentData(),
        }
        self._batch.append(entry)
        self._refresh_batch_table()

        # Réinitialiser les champs article (garder le contexte)
        self.name_input.clear()
        self.ref_input.clear()
        self.desc_input.clear()
        self.qty_spin.setValue(1)
        self.qty_min_spin.setValue(0)
        self.mode_combo.setCurrentIndex(0)
        self.manual_price.setValue(0)
        self.notes_input.clear()
        self.name_input.setFocus()

    def _remove_selected(self):
        rows = sorted({idx.row() for idx in self.batch_table.selectedIndexes()}, reverse=True)
        for r in rows:
            if 0 <= r < len(self._batch):
                del self._batch[r]
        self._refresh_batch_table()

    def _refresh_batch_table(self):
        self.batch_table.setRowCount(len(self._batch))
        for i, entry in enumerate(self._batch):
            vals = [
                entry["name"],
                entry["reference"],
                entry["description"],
                str(entry["quantity"]),
                str(entry["quantity_min"]),
                entry["price_mode"],
                f"{entry['price_manual']:.2f} €" if entry["price_manual"] is not None else "auto",
                entry["notes"],
            ]
            for j, v in enumerate(vals):
                self.batch_table.setItem(i, j, QTableWidgetItem(v))
        count = len(self._batch)
        self.batch_count_label.setText(f"{count} article(s) dans le lot")
        self.btn_validate.setEnabled(count > 0)

    # ─── Résultat ───
    def get_articles(self) -> list[Article]:
        """Retourne la liste des articles construits depuis le lot."""
        location_id = self.loc_combo.currentData()
        category_id = self.cat_combo.currentData()
        supplier_id = self.sup_combo.currentData()

        articles = []
        for entry in self._batch:
            articles.append(Article(
                reference=entry["reference"],
                name=entry["name"],
                description=entry["description"],
                category_id=category_id,
                location_id=location_id,
                supplier_id=supplier_id,
                quantity=entry["quantity"],
                quantity_min=entry["quantity_min"],
                price_mode=entry["price_mode"],
                price_manual=entry["price_manual"],
                notes=entry["notes"],
                tool_type_id=entry["tool_type_id"],
            ))
        return articles


# ═════════════════════════════════════════════════════════
#  Dialog Création de type d'outil
# ═════════════════════════════════════════════════════════
class _CreateToolTypeDialog(QDialog):
    """Petit dialog pour créer un nouveau type d'outil dans le catalogue."""

    def __init__(self, parent=None, tool_categories=None):
        super().__init__(parent)
        self.setWindowTitle("Créer un type d'outil")
        self.setMinimumWidth(450)
        self._tool_categories = tool_categories or []

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cat_combo = QComboBox()
        for tc in self._tool_categories:
            self.cat_combo.addItem(tc.name, tc.id)
        _form_row(form, "Catégorie outillage :", self.cat_combo)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du type (ex: Tournevis Torx T45)")
        _form_row(form, "Nom :", self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description (ex: Étoile T45)")
        _form_row(form, "Description :", self.desc_input)

        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Référence par défaut (optionnel)")
        _form_row(form, "Réf. par défaut :", self.ref_input)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 999999)
        self.price_spin.setDecimals(2)
        self.price_spin.setSuffix(" €")
        _form_row(form, "Prix par défaut :", self.price_spin)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Champ requis", "Le nom du type est obligatoire.")
            return
        if not self.cat_combo.currentData():
            QMessageBox.warning(self, "Champ requis", "Sélectionnez une catégorie.")
            return
        self.accept()

    def get_tool_type(self):
        from ...core.models import ToolType
        return ToolType(
            category_id=self.cat_combo.currentData(),
            name=self.name_input.text().strip(),
            description=self.desc_input.text().strip(),
            default_ref=self.ref_input.text().strip(),
            default_price=self.price_spin.value(),
        )
