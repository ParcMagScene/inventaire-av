"""
pdf_exporter.py — Export PDF professionnel avec ReportLab.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak,
)

from . import database as db
from .models import Article

BASE_DIR = Path(__file__).resolve().parent.parent

# Couleurs corporate
DARK_BG = colors.HexColor("#2b2d31")
TURQUOISE = colors.HexColor("#00bfa5")
VIOLET = colors.HexColor("#7c4dff")
HEADER_BG = colors.HexColor("#363940")
ROW_EVEN = colors.HexColor("#f5f5f5")
ROW_ODD = colors.white


class PDFExporter:
    """Génère un rapport PDF de l'inventaire."""

    def __init__(self, db_path=None):
        self.db_path = db_path

    def export(self, output_path: str,
               category_id: int | None = None,
               location_id: int | None = None) -> str:
        """Exporte l'inventaire filtré vers un fichier PDF. Retourne le chemin."""
        articles = db.get_articles(self.db_path,
                                   category_id=category_id,
                                   location_id=location_id)
        categories = {c.id: c for c in db.get_categories(self.db_path)}
        locations = {l.id: l for l in db.get_locations(self.db_path)}

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        # ─── En-tête avec logo ────────────────────────
        logo_path = BASE_DIR / "ui" / "icons" / "logo.svg"
        # ReportLab ne gère pas nativement SVG pour Image, on utilise PNG si dispo
        logo_png = BASE_DIR / "ui" / "icons" / "logo.png"
        header_parts = []
        if logo_png.exists():
            header_parts.append(Image(str(logo_png), width=3 * cm, height=3 * cm))
        elif logo_path.exists():
            try:
                from reportlab.graphics import renderSVG
                from svglib.svglib import svg2rlg
                drawing = svg2rlg(str(logo_path))
                if drawing:
                    drawing.width = 3 * cm
                    drawing.height = 3 * cm
                    header_parts.append(drawing)
            except ImportError:
                pass

        date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
        title_style = ParagraphStyle(
            "Title", parent=styles["Title"],
            fontSize=20, textColor=TURQUOISE, spaceAfter=4 * mm,
        )
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"],
            fontSize=11, textColor=colors.gray,
        )

        elements.append(Paragraph(f"Inventaire – {date_str}", title_style))
        elements.append(Paragraph("Rapport généré automatiquement par Inventaire AV", subtitle_style))
        elements.append(Spacer(1, 8 * mm))

        # ─── Tableau principal ────────────────────────
        if articles:
            elements.append(Paragraph("Liste des articles", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_article_table(articles, styles))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux par catégorie ────────────────────
        cat_totals = self._totals_by_category(articles, categories)
        if cat_totals:
            elements.append(Paragraph("Totaux par catégorie", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_summary_table(cat_totals, "Catégorie"))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux par emplacement ──────────────────
        loc_totals = self._totals_by_location(articles, locations)
        if loc_totals:
            elements.append(Paragraph("Totaux par emplacement", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_summary_table(loc_totals, "Emplacement"))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux globaux ─────────────────────────
        elements.append(Paragraph("Totaux globaux", styles["Heading2"]))
        elements.append(Spacer(1, 3 * mm))
        elements.extend(self._build_global_totals(articles))

        doc.build(elements)
        return output_path

    # ─── Tableau articles ────────────────────────────
    def _build_article_table(self, articles: List[Article], styles) -> list:
        cell_style = ParagraphStyle("Cell", fontSize=7, leading=9)
        header_style = ParagraphStyle("HCell", fontSize=7, leading=9,
                                      textColor=colors.white, fontName="Helvetica-Bold")

        headers = ["Réf.", "Nom", "Catégorie", "Emplacement", "Qté",
                    "Prix Bas", "Prix Moy.", "Prix Haut", "Mode", "Confiance"]

        data = [[Paragraph(h, header_style) for h in headers]]
        for a in articles:
            data.append([
                Paragraph(str(a.reference), cell_style),
                Paragraph(str(a.name), cell_style),
                Paragraph(str(a.category_name), cell_style),
                Paragraph(str(a.location_name), cell_style),
                Paragraph(str(a.quantity), cell_style),
                Paragraph(f"{a.price_low:.2f} €", cell_style),
                Paragraph(f"{a.price_avg:.2f} €", cell_style),
                Paragraph(f"{a.price_high:.2f} €", cell_style),
                Paragraph(str(a.price_mode), cell_style),
                Paragraph(str(a.confidence), cell_style),
            ])

        col_widths = [2.2*cm, 4.5*cm, 2.8*cm, 2.8*cm, 1.2*cm,
                      2*cm, 2*cm, 2*cm, 2*cm, 2*cm]

        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (4, 1), (7, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        for i in range(1, len(data)):
            bg = ROW_EVEN if i % 2 == 0 else ROW_ODD
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
        table.setStyle(TableStyle(style_cmds))
        return [table]

    # ─── Totaux ─────────────────────────────────────
    def _totals_by_category(self, articles, categories):
        totals = {}
        for a in articles:
            name = a.category_name or "Sans catégorie"
            if name not in totals:
                totals[name] = {"qty": 0, "value": 0.0}
            totals[name]["qty"] += a.quantity
            totals[name]["value"] += a.quantity * a.price_avg
        return totals

    def _totals_by_location(self, articles, locations):
        totals = {}
        for a in articles:
            name = a.location_name or "Sans emplacement"
            if name not in totals:
                totals[name] = {"qty": 0, "value": 0.0}
            totals[name]["qty"] += a.quantity
            totals[name]["value"] += a.quantity * a.price_avg
        return totals

    def _build_summary_table(self, totals: dict, label: str) -> list:
        data = [[label, "Quantité", "Valeur estimée"]]
        for name, vals in sorted(totals.items()):
            data.append([name, str(vals["qty"]), f"{vals['value']:.2f} €"])
        total_qty = sum(v["qty"] for v in totals.values())
        total_val = sum(v["value"] for v in totals.values())
        data.append(["TOTAL", str(total_qty), f"{total_val:.2f} €"])

        table = Table(data, colWidths=[8*cm, 3*cm, 4*cm])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, -1), (-1, -1), TURQUOISE),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
        for i in range(1, len(data) - 1):
            bg = ROW_EVEN if i % 2 == 0 else ROW_ODD
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
        table.setStyle(TableStyle(style_cmds))
        return [table]

    def _build_global_totals(self, articles: List[Article]) -> list:
        total_qty = sum(a.quantity for a in articles)
        total_val_low = sum(a.quantity * a.price_low for a in articles)
        total_val_avg = sum(a.quantity * a.price_avg for a in articles)
        total_val_high = sum(a.quantity * a.price_high for a in articles)

        data = [
            ["Métrique", "Valeur"],
            ["Nombre de références", str(len(articles))],
            ["Quantité totale", str(total_qty)],
            ["Valeur totale (fourchette basse)", f"{total_val_low:.2f} €"],
            ["Valeur totale (prix moyen)", f"{total_val_avg:.2f} €"],
            ["Valeur totale (fourchette haute)", f"{total_val_high:.2f} €"],
        ]
        table = Table(data, colWidths=[8*cm, 5*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 1), (-1, -1), ROW_EVEN),
        ]))
        return [table]
