"""
about_view.py — Écran À propos avec logo.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QHBoxLayout,
)

ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


class AboutView(QWidget):
    """Écran À propos."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # ── Logo ──
        logo_path = ICONS_DIR / "app_icon.svg"
        if logo_path.exists():
            renderer = QSvgRenderer(str(logo_path))
            image = QImage(256, 256, QImage.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            pixmap = QPixmap.fromImage(image)

            logo_label = QLabel()
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)

        # ── Titre ──
        title = QLabel("Inventaire AV")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px;")
        layout.addWidget(title)

        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        layout.addWidget(version)

        layout.addSpacing(20)

        # ── Description ──
        grp = QGroupBox("À propos")
        grp_layout = QVBoxLayout(grp)

        desc = QLabel(
            "Application de gestion d'inventaire de consommables et pièces "
            "détachées audiovisuelles.\n\n"
            "Conçue pour les chefs de parc, cette application propose :\n"
            "• Gestion complète des articles, catégories, emplacements et fournisseurs\n"
            "• Moteur intelligent de suggestion de prix avec fusion multi-sources\n"
            "• Export PDF professionnel avec totaux et statistiques\n"
            "• Trois modes de prix : Manuel, Automatique et Mixte\n"
            "• Indice de confiance sur chaque prix suggéré\n\n"
            "Technologies : Python 3 · PySide6 (Qt6) · SQLite · ReportLab"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; line-height: 1.6;")
        grp_layout.addWidget(desc)

        layout.addWidget(grp)

        # ── Crédits ──
        grp2 = QGroupBox("Informations techniques")
        grp2_layout = QVBoxLayout(grp2)
        tech = QLabel(
            "• Base de données : SQLite (fichier local inventaire.db)\n"
            "• Interface : PySide6 / Qt6 — thème sombre professionnel\n"
            "• Moteur de prix : fusion pondérée multi-sources + détection aberrations\n"
            "• Export : ReportLab (PDF paysage A4)\n"
            "• Packaging : PyInstaller + Inno Setup"
        )
        tech.setWordWrap(True)
        tech.setStyleSheet("font-size: 12px; color: #a0a0a0;")
        grp2_layout.addWidget(tech)
        layout.addWidget(grp2)

        layout.addStretch()

    def refresh(self):
        pass
