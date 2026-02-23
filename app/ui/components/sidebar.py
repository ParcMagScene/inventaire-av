"""
sidebar.py — Menu latéral vertical avec icônes SVG et navigation.
"""
from pathlib import Path

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem,
)

ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


class SidebarButton(QPushButton):
    """Bouton du menu latéral avec icône et texte."""

    def __init__(self, text: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarBtn")
        self.setText(f"  {text}")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        icon_path = ICONS_DIR / f"{icon_name}.svg"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
            self.setIconSize(QSize(20, 20))

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(42)


class Sidebar(QWidget):
    """Sidebar de navigation principale."""

    page_changed = Signal(int)

    PAGES = [
        ("Dashboard", "dashboard"),
        ("Inventaire", "inventory"),
        ("Catégories", "category"),
        ("Emplacements", "location"),
        ("Fournisseurs", "supplier"),
        ("Paramètres prix", "price"),
        ("Export", "pdf"),
        ("À propos", "about"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Titre
        title = QLabel("Inventaire AV")
        title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel("v2.0.0")
        version.setObjectName("sidebarVersion")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(12)

        # Boutons
        self.buttons: list[SidebarButton] = []
        for i, (label, icon_name) in enumerate(self.PAGES):
            btn = SidebarButton(label, icon_name)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Sélection initiale
        if self.buttons:
            self.buttons[0].setChecked(True)

    def _on_click(self, index: int):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

    def set_active(self, index: int):
        self._on_click(index)
