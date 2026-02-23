"""
pdf_exporter.py — Export PDF professionnel avec ReportLab.

Améliorations v2 :
 - Totaux par ligne (Total Bas / Moyen / Haut)
 - Totaux par fournisseur
 - Mode de prix utilisé en en-tête
 - Pied de page avec date de génération
 - Totaux globaux améliorés (bas/moyen/haut)
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
from .totals_engine import TotalsEngine

BASE_DIR = Path(__file__).resolve().parent.parent

# Couleurs corporate
DARK_BG = colors.HexColor("#2b2d31")
TURQUOISE = colors.HexColor("#00bfa5")
VIOLET = colors.HexColor("#7c4dff")
HEADER_BG = colors.HexColor("#363940")
ROW_EVEN = colors.HexColor("#f5f5f5")
ROW_ODD = colors.white


def _footer(canvas, doc):
    """Pied de page avec date et numéro de page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.gray)
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    canvas.drawString(1.5 * cm, 1 * cm,
                      f"Inventaire AV — Rapport généré le {date_str}")
    canvas.drawRightString(
        doc.pagesize[0] - 1.5 * cm, 1 * cm,
        f"Page {canvas.getPageNumber()}"
    )
    canvas.restoreState()


class PDFExporter:
    """Génère un rapport PDF de l'inventaire."""

    def __init__(self, db_path=None):
        self.db_path = db_path
        self.totals = TotalsEngine(db_path)

    def export(self, output_path: str,
               category_id: int | None = None,
               location_id: int | None = None) -> str:
        """Exporte l'inventaire filtré vers un fichier PDF. Retourne le chemin."""
        articles = db.get_articles(self.db_path,
                                   category_id=category_id,
                                   location_id=location_id)
        categories = {c.id: c for c in db.get_categories(self.db_path)}
        locations = {l.id: l for l in db.get_locations(self.db_path)}
        suppliers = {s.id: s for s in db.get_suppliers(self.db_path)}

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=2 * cm,
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

        # ─── Tableau principal avec totaux par ligne ──
        if articles:
            elements.append(Paragraph("Liste des articles", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_article_table(articles, styles))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux par catégorie ────────────────────
        cat_totals = self.totals.totals_by_category(articles)
        if cat_totals:
            elements.append(Paragraph("Totaux par catégorie", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_summary_table(cat_totals, "Catégorie"))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux par emplacement ──────────────────
        loc_totals = self.totals.totals_by_location(articles)
        if loc_totals:
            elements.append(Paragraph("Totaux par emplacement", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_summary_table(loc_totals, "Emplacement"))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux par fournisseur ──────────────────
        sup_totals = self.totals.totals_by_supplier(articles)
        if sup_totals:
            elements.append(Paragraph("Totaux par fournisseur", styles["Heading2"]))
            elements.append(Spacer(1, 3 * mm))
            elements.extend(self._build_summary_table(sup_totals, "Fournisseur"))
            elements.append(Spacer(1, 8 * mm))

        # ─── Totaux globaux ─────────────────────────
        elements.append(Paragraph("Totaux globaux", styles["Heading2"]))
        elements.append(Spacer(1, 3 * mm))
        elements.extend(self._build_global_totals(articles))

        doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
        return output_path

    # ─── Tableau articles avec totaux par ligne ──────
    def _build_article_table(self, articles: List[Article], styles) -> list:
        cell_style = ParagraphStyle("Cell", fontSize=6.5, leading=8)
        header_style = ParagraphStyle("HCell", fontSize=6.5, leading=8,
                                      textColor=colors.white, fontName="Helvetica-Bold")

        headers = ["Réf.", "Nom", "Cat.", "Empl.", "Qté",
                    "P.Bas", "P.Moy.", "P.Haut",
                    "T.Bas", "T.Moy.", "T.Haut",
                    "Mode", "Conf."]

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
                Paragraph(f"{a.total_low:.2f} €", cell_style),
                Paragraph(f"{a.total_avg:.2f} €", cell_style),
                Paragraph(f"{a.total_high:.2f} €", cell_style),
                Paragraph(str(a.price_mode), cell_style),
                Paragraph(f"{a.confidence} ({a.confidence_score})", cell_style),
            ])

        col_widths = [1.8*cm, 3.5*cm, 2*cm, 2*cm, 1*cm,
                      1.6*cm, 1.6*cm, 1.6*cm,
                      1.8*cm, 1.8*cm, 1.8*cm,
                      1.5*cm, 1.8*cm]

        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6.5),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (4, 1), (10, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            # Highlight totaux par ligne
            ("BACKGROUND", (8, 0), (10, 0), TURQUOISE),
        ]
        for i in range(1, len(data)):
            bg = ROW_EVEN if i % 2 == 0 else ROW_ODD
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
        table.setStyle(TableStyle(style_cmds))
        return [table]

    # ─── Totaux par groupe (amélioré avec bas/moyen/haut) ──
    def _build_summary_table(self, totals: dict, label: str) -> list:
        data = [[label, "Quantité", "Valeur Basse", "Valeur Moyenne", "Valeur Haute"]]
        for name, vals in sorted(totals.items()):
            data.append([
                name, str(vals["qty"]),
                f"{vals['low']:.2f} €",
                f"{vals['avg']:.2f} €",
                f"{vals['high']:.2f} €",
            ])
        total_qty = sum(v["qty"] for v in totals.values())
        total_low = sum(v["low"] for v in totals.values())
        total_avg = sum(v["avg"] for v in totals.values())
        total_high = sum(v["high"] for v in totals.values())
        data.append([
            "TOTAL", str(total_qty),
            f"{total_low:.2f} €",
            f"{total_avg:.2f} €",
            f"{total_high:.2f} €",
        ])

        table = Table(data, colWidths=[6*cm, 2*cm, 3.5*cm, 3.5*cm, 3.5*cm])
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
        gt = self.totals.global_totals(articles)

        data = [
            ["Métrique", "Valeur"],
            ["Nombre de références", str(gt["nb_references"])],
            ["Quantité totale", str(gt["total_quantity"])],
            ["Valeur totale (fourchette basse)", f"{gt['total_low']:.2f} €"],
            ["Valeur totale (prix moyen)", f"{gt['total_avg']:.2f} €"],
            ["Valeur totale (fourchette haute)", f"{gt['total_high']:.2f} €"],
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
