"""
data_table.py — Tableau moderne avec tri, recherche et édition.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QPushButton, QHeaderView, QAbstractItemView,
    QLabel,
)


class DataTable(QWidget):
    """Composant tableau générique avec barre de recherche et filtres."""

    row_double_clicked = Signal(int)      # émet l'index de la ligne
    selection_changed = Signal()

    def __init__(self, columns: list[str], parent=None, *,
                 editable: bool = False,
                 filter_column: int | None = None,
                 filter_items: list[str] | None = None):
        super().__init__(parent)
        self._columns = columns
        self._all_data: list[list] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Toolbar ──────────────────────────────
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText("🔍  Rechercher…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_input, 2)

        if filter_column is not None and filter_items:
            self.filter_combo = QComboBox()
            self.filter_combo.addItem("Tous")
            self.filter_combo.addItems(filter_items)
            self.filter_combo.currentTextChanged.connect(self._apply_filter)
            toolbar.addWidget(self.filter_combo, 1)
        else:
            self.filter_combo = None

        self.count_label = QLabel("0 éléments")
        self.count_label.setObjectName("statLabel")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # ── Table ────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        for i in range(len(columns)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        if not editable:
            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            self.table.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.table.doubleClicked.connect(
            lambda idx: self.row_double_clicked.emit(idx.row())
        )
        self.table.itemSelectionChanged.connect(self.selection_changed.emit)

        layout.addWidget(self.table)

        self._filter_col = filter_column

    # ─── API ─────────────────────────────────────
    def set_data(self, rows: list[list]):
        """Remplace toutes les données du tableau."""
        self._all_data = rows
        self._apply_filter()

    def _apply_filter(self, *_):
        search = self.search_input.text().lower()
        combo_text = self.filter_combo.currentText() if self.filter_combo else "Tous"

        filtered = []
        for row in self._all_data:
            # Filtre combo
            if combo_text != "Tous" and self._filter_col is not None:
                if str(row[self._filter_col]).lower() != combo_text.lower():
                    continue
            # Filtre texte
            if search:
                if not any(search in str(cell).lower() for cell in row):
                    continue
            filtered.append(row)

        self._populate(filtered)

    def _populate(self, rows: list[list]):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else "")
                # Alignement numérique à droite
                if isinstance(value, (int, float)):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setData(Qt.UserRole, value)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
        self.count_label.setText(f"{len(rows)} éléments")

    def selected_row_index(self) -> int | None:
        """Renvoie l'index dans _all_data de la ligne sélectionnée ou None."""
        sel = self.table.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        # Reconstituer la ligne affichée puis trouver dans _all_data
        displayed = []
        for c in range(self.table.columnCount()):
            item = self.table.item(row, c)
            displayed.append(item.text() if item else "")
        for i, data_row in enumerate(self._all_data):
            if [str(v) if v is not None else "" for v in data_row] == displayed:
                return i
        return row

    def selected_row_data(self) -> list | None:
        idx = self.selected_row_index()
        if idx is not None and idx < len(self._all_data):
            return self._all_data[idx]
        return None

    def clear(self):
        self._all_data.clear()
        self.table.setRowCount(0)
        self.count_label.setText("0 éléments")
