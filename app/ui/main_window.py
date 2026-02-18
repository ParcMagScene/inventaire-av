"""
main_window.py — Fenêtre principale avec sidebar + stack de vues.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QStatusBar,
)
from PySide6.QtGui import QIcon

from .components.sidebar import Sidebar
from .views.inventory_view import InventoryView
from .views.categories_view import CategoriesView
from .views.locations_view import LocationsView
from .views.suppliers_view import SuppliersView
from .views.price_settings_view import PriceSettingsView
from .views.export_view import ExportView
from .views.about_view import AboutView

STYLES_PATH = Path(__file__).resolve().parent / "styles_dark.qss"


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application Inventaire AV."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventaire AV — Gestion de parc audiovisuel")
        self.setMinimumSize(1024, 700)
        self.resize(1280, 800)

        # ── Icône de fenêtre ──
        icon_path = Path(__file__).resolve().parent / "icons" / "app_icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # ── Chargement du thème ──
        if STYLES_PATH.exists():
            with open(STYLES_PATH, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        # ── Widget central ──
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        main_layout.addWidget(self.sidebar)

        # ── Stack de vues ──
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        # Instanciation des vues
        self.views = [
            InventoryView(),
            CategoriesView(),
            LocationsView(),
            SuppliersView(),
            PriceSettingsView(),
            ExportView(),
            AboutView(),
        ]
        for v in self.views:
            self.stack.addWidget(v)

        # ── Barre d'état ──
        status = QStatusBar()
        status.showMessage("Inventaire AV v1.0.0 — Prêt")
        self.setStatusBar(status)

    def _switch_page(self, index: int):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            # Rafraîchir la vue active
            view = self.views[index]
            if hasattr(view, "refresh"):
                view.refresh()
