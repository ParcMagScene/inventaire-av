"""
dashboard_view.py — Tableau de bord métier avec indicateurs, graphiques et alertes.
"""
from datetime import datetime

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QFont, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout,
    QScrollArea, QSizePolicy, QFrame,
)

from ...core import database as db
from ...core.totals_engine import TotalsEngine


# ─── Couleurs du thème ───────────────────────────────────
TURQUOISE = "#00bfa5"
VIOLET = "#7c4dff"
DANGER = "#ff5252"
WARNING = "#ffab40"
SUCCESS = "#69f0ae"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#a0a0a0"
CARD_BG = "#313338"
BAR_COLORS = [
    "#00bfa5", "#7c4dff", "#ff5252", "#ffab40",
    "#69f0ae", "#42a5f5", "#ab47bc", "#ef5350",
    "#26c6da", "#d4e157", "#ffa726", "#8d6e63",
]


# ═══════════════════════════════════════════════════════════
#  Widget barre horizontale simple (graphique léger)
# ═══════════════════════════════════════════════════════════
class HorizontalBarChart(QWidget):
    """Graphique en barres horizontales léger (sans dépendance QtCharts)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[str, float, str]] = []  # (label, value, color)
        self._max_value = 1.0
        self.setMinimumHeight(40)

    def set_data(self, data: list[tuple[str, float]], max_value: float = None):
        """data = [(label, value), ...]"""
        colors = BAR_COLORS
        self._data = [
            (label, value, colors[i % len(colors)])
            for i, (label, value) in enumerate(data)
        ]
        self._max_value = max_value or max((v for _, v, _ in self._data), default=1.0)
        bar_height = 32
        self.setMinimumHeight(max(40, len(self._data) * bar_height + 10))
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._data)
        bar_height = min(28, max(16, (h - 10) // max(n, 1)))
        label_width = min(150, w // 3)
        bar_area = w - label_width - 80  # espace pour la valeur à droite

        font_label = QFont("Segoe UI", 9)
        font_value = QFont("Segoe UI", 9, QFont.Bold)

        y = 5
        for label, value, color in self._data:
            # Label
            painter.setFont(font_label)
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(
                QRectF(4, y, label_width - 8, bar_height),
                Qt.AlignVCenter | Qt.AlignRight, label
            )

            # Barre
            bar_w = (value / self._max_value * bar_area) if self._max_value > 0 else 0
            bar_w = max(2, bar_w)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(
                QRectF(label_width + 4, y + 2, bar_w, bar_height - 4),
                4, 4,
            )

            # Valeur
            painter.setFont(font_value)
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(
                QRectF(label_width + bar_w + 8, y, 70, bar_height),
                Qt.AlignVCenter | Qt.AlignLeft, f"{value:,.0f} €"
            )

            y += bar_height

        painter.end()


# ═══════════════════════════════════════════════════════════
#  Widget KPI (indicateur chiffré)
# ═══════════════════════════════════════════════════════════
class KPICard(QFrame):
    """Carte KPI avec valeur, titre et couleur d'accent."""

    def __init__(self, title: str, value: str = "0",
                 accent: str = TURQUOISE, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: {CARD_BG};
                border: 1px solid #3f4147;
                border-radius: 10px;
                border-left: 4px solid {accent};
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.val_label = QLabel(value)
        self.val_label.setStyleSheet(
            f"color: {accent}; font-size: 24px; font-weight: bold; background: transparent;"
        )
        self.val_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.val_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

    def set_value(self, value: str):
        self.val_label.setText(value)


# ═══════════════════════════════════════════════════════════
#  Vue Dashboard
# ═══════════════════════════════════════════════════════════
class DashboardView(QWidget):
    """Tableau de bord métier complet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = TotalsEngine()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ── Titre ──
        title = QLabel("Tableau de bord")
        title.setObjectName("sectionTitle")
        main_layout.addWidget(title)

        # ── KPIs principaux ──
        kpi_layout = QGridLayout()
        kpi_layout.setSpacing(12)

        self.kpi_refs = KPICard("Références", accent=TURQUOISE)
        self.kpi_qty = KPICard("Quantité totale", accent=VIOLET)
        self.kpi_value_low = KPICard("Valeur (basse)", accent=WARNING)
        self.kpi_value_avg = KPICard("Valeur (moyenne)", accent=TURQUOISE)
        self.kpi_value_high = KPICard("Valeur (haute)", accent=SUCCESS)
        self.kpi_alerts = KPICard("Stock faible", accent=DANGER)

        kpi_layout.addWidget(self.kpi_refs, 0, 0)
        kpi_layout.addWidget(self.kpi_qty, 0, 1)
        kpi_layout.addWidget(self.kpi_value_low, 0, 2)
        kpi_layout.addWidget(self.kpi_value_avg, 0, 3)
        kpi_layout.addWidget(self.kpi_value_high, 0, 4)
        kpi_layout.addWidget(self.kpi_alerts, 0, 5)

        main_layout.addLayout(kpi_layout)

        # ── Graphiques ──
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        # Répartition par catégorie
        cat_grp = QGroupBox("Valeur par catégorie")
        cat_layout = QVBoxLayout(cat_grp)
        self.cat_chart = HorizontalBarChart()
        cat_layout.addWidget(self.cat_chart)
        charts_layout.addWidget(cat_grp)

        # Répartition par emplacement
        loc_grp = QGroupBox("Valeur par emplacement")
        loc_layout = QVBoxLayout(loc_grp)
        self.loc_chart = HorizontalBarChart()
        loc_layout.addWidget(self.loc_chart)
        charts_layout.addWidget(loc_grp)

        main_layout.addLayout(charts_layout)

        # ── Fournisseurs + Alertes ──
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)

        # Valeur par fournisseur
        sup_grp = QGroupBox("Valeur par fournisseur")
        sup_layout = QVBoxLayout(sup_grp)
        self.sup_chart = HorizontalBarChart()
        sup_layout.addWidget(self.sup_chart)
        bottom_layout.addWidget(sup_grp)

        # Alertes stock bas
        alert_grp = QGroupBox("⚠ Alertes stock bas")
        alert_layout = QVBoxLayout(alert_grp)
        self.alerts_label = QLabel("Aucune alerte")
        self.alerts_label.setWordWrap(True)
        self.alerts_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        alert_layout.addWidget(self.alerts_label)
        bottom_layout.addWidget(alert_grp)

        main_layout.addLayout(bottom_layout)

        # ── Dernières mises à jour ──
        recent_grp = QGroupBox("Dernières mises à jour de prix")
        recent_layout = QVBoxLayout(recent_grp)
        self.recent_label = QLabel("Chargement...")
        self.recent_label.setWordWrap(True)
        self.recent_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        recent_layout.addWidget(self.recent_label)
        main_layout.addWidget(recent_grp)

        main_layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.refresh()

    # ─── Rafraîchir les données ──────────────────────
    def refresh(self):
        articles = db.get_articles()
        summary = self.engine.full_summary(articles)
        gt = summary["global"]

        # KPIs
        self.kpi_refs.set_value(str(gt["nb_references"]))
        self.kpi_qty.set_value(str(gt["total_quantity"]))
        self.kpi_value_low.set_value(f"{gt['total_low']:,.2f} €")
        self.kpi_value_avg.set_value(f"{gt['total_avg']:,.2f} €")
        self.kpi_value_high.set_value(f"{gt['total_high']:,.2f} €")
        self.kpi_alerts.set_value(str(summary["low_stock_count"]))

        # Graphique catégories
        cat_data = [
            (name, vals["avg"])
            for name, vals in sorted(
                summary["by_category"].items(),
                key=lambda x: x[1]["avg"], reverse=True
            )
        ]
        self.cat_chart.set_data(cat_data)

        # Graphique emplacements
        loc_data = [
            (name, vals["avg"])
            for name, vals in sorted(
                summary["by_location"].items(),
                key=lambda x: x[1]["avg"], reverse=True
            )
        ]
        self.loc_chart.set_data(loc_data)

        # Graphique fournisseurs
        sup_data = [
            (name, vals["avg"])
            for name, vals in sorted(
                summary["by_supplier"].items(),
                key=lambda x: x[1]["avg"], reverse=True
            )
        ]
        self.sup_chart.set_data(sup_data)

        # Alertes stock bas
        low_stock = self.engine.low_stock_alerts(articles)
        if low_stock:
            lines = []
            for a in low_stock[:15]:  # Limiter à 15
                lines.append(
                    f'<span style="color:{DANGER};">●</span> '
                    f'<b>{a.name}</b> ({a.reference}) — '
                    f'{a.quantity}/{a.quantity_min} en stock'
                )
            self.alerts_label.setText("<br>".join(lines))
        else:
            self.alerts_label.setText(
                f'<span style="color:{SUCCESS};">✓</span> '
                'Tous les stocks sont au-dessus du seuil minimum.'
            )

        # Dernières mises à jour
        recent = db.get_recent_updates(limit=10)
        if recent:
            lines = []
            for r in recent:
                lines.append(
                    f'<b>{r.get("name", "")}</b> ({r.get("reference", "")}) — '
                    f'{r.get("price_avg", 0):.2f} € — {r.get("updated_at", "")}'
                )
            self.recent_label.setText("<br>".join(lines))
        else:
            self.recent_label.setText("Aucune donnée récente.")
