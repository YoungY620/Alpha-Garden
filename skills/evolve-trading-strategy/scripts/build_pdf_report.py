#!/usr/bin/env python3
"""Build a restrained financial research PDF from a structured JSON report."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#13283F")
BLUE = colors.HexColor("#2C5F8A")
SLATE = colors.HexColor("#4E5D6C")
PALE = colors.HexColor("#EDF2F6")
RISK = colors.HexColor("#A04A3A")
INK = colors.HexColor("#17212B")

EN_LABELS = {
    "research_only": "Research Only",
    "page": "Page",
    "field": "Field",
    "value": "Value",
    "executive_summary": "Executive Summary",
    "headline_evidence": "Headline Evidence",
    "metric": "Metric",
    "train": "Train",
    "validation": "Validation",
    "sealed_test": "Sealed Test",
    "notes": "Notes",
    "reproducibility": "Reproducibility and Disclosures",
    "artifact": "Artifact",
    "checksum": "SHA-256",
}

ZH_LABELS = {
    "research_only": "仅供研究",
    "page": "第",
    "field": "项目",
    "value": "内容",
    "executive_summary": "执行摘要",
    "headline_evidence": "核心证据",
    "metric": "指标",
    "train": "训练集",
    "validation": "验证集",
    "sealed_test": "封存测试",
    "notes": "说明",
    "reproducibility": "复现信息与披露",
    "artifact": "产物",
    "checksum": "SHA-256",
}


def _discover_font(explicit: Path | None, preferred_tokens: tuple[str, ...]) -> Path:
    if explicit:
        if not explicit.is_file():
            raise SystemExit(f"font not found: {explicit}")
        return explicit
    fonts: list[Path] = []
    try:
        from matplotlib import font_manager

        fonts.extend(Path(path) for path in font_manager.findSystemFonts(fontext="ttf"))
    except ImportError:
        pass
    from reportlab import rl_config

    for directory in rl_config.TTFSearchPath:
        root = Path(directory)
        if root.is_dir():
            fonts.extend(root.rglob("*.ttf"))
            fonts.extend(root.rglob("*.otf"))
            fonts.extend(root.rglob("*.ttc"))
    lowered = [(path, path.name.lower().replace(" ", "")) for path in fonts]
    for token in preferred_tokens:
        normalized = token.lower().replace(" ", "")
        for path, name in lowered:
            if normalized in name:
                return path
    for path in fonts:
        if path.name.lower() == "vera.ttf":
            return path
    raise SystemExit("no embeddable font found; provide --font-sans and --font-serif")


def _default_subfont(path: Path, role: str) -> int:
    name = path.name.lower()
    if name == "songti.ttc" and role == "serif":
        return 6
    if name == "stheiti medium.ttc" and role == "sans":
        return 1
    return 0


def _register_fonts(
    sans: Path | None,
    serif: Path | None,
    sans_index: int | None,
    serif_index: int | None,
    required_codepoints: set[int],
) -> tuple[str, str]:
    sans_path = _discover_font(sans, ("SourceHanSans", "NotoSansCJK", "NotoSansSC", "STHeiti", "DejaVuSans"))
    serif_path = _discover_font(serif, ("SourceHanSerif", "NotoSerifCJK", "NotoSerifSC", "Songti", "DejaVuSerif"))
    sans_font = TTFont("ResearchSans", str(sans_path), subfontIndex=_default_subfont(sans_path, "sans") if sans_index is None else sans_index)
    serif_font = TTFont("ResearchSerif", str(serif_path), subfontIndex=_default_subfont(serif_path, "serif") if serif_index is None else serif_index)
    missing_sans = required_codepoints - set(sans_font.face.charWidths)
    missing_serif = required_codepoints - set(serif_font.face.charWidths)
    if missing_sans:
        raise SystemExit("sans font does not cover all report characters; provide --font-sans")
    if missing_serif:
        if not (required_codepoints - set(sans_font.face.charWidths)):
            serif_font = TTFont("ResearchSerif", str(sans_path), subfontIndex=_default_subfont(sans_path, "sans") if sans_index is None else sans_index)
        else:
            raise SystemExit("serif font does not cover all report characters; provide --font-serif")
    pdfmetrics.registerFont(sans_font)
    pdfmetrics.registerFont(serif_font)
    return "ResearchSans", "ResearchSerif"


def _text(value: object) -> str:
    return html.escape(str(value)).replace("\n", "<br/>")


def _styles(sans: str, serif: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName=sans, fontSize=24, leading=29, textColor=NAVY, alignment=TA_LEFT, spaceAfter=9 * mm),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName=sans, fontSize=10, leading=14, textColor=SLATE, spaceAfter=5 * mm),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName=sans, fontSize=15, leading=19, textColor=NAVY, spaceBefore=5 * mm, spaceAfter=3 * mm),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName=sans, fontSize=11, leading=15, textColor=BLUE, spaceBefore=3 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName=serif, fontSize=9.2, leading=14, textColor=INK, spaceAfter=2.5 * mm),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName=sans, fontSize=7.5, leading=10, textColor=SLATE),
        "risk": ParagraphStyle("Risk", parent=base["BodyText"], fontName=serif, fontSize=9.2, leading=14, textColor=RISK, leftIndent=3 * mm, borderColor=RISK, borderWidth=0.8, borderPadding=3 * mm, spaceAfter=3 * mm),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName=sans, fontSize=7.5, leading=9.5, textColor=INK, alignment=TA_LEFT),
        "cover_mark": ParagraphStyle("CoverMark", parent=base["Normal"], fontName=sans, fontSize=9, leading=12, textColor=RISK, alignment=TA_CENTER),
    }
    for item in styles.values():
        item.bulletFontName = sans
    return styles


def _page(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 12 * mm, width, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("ResearchSans", 7)
    canvas.drawString(18 * mm, height - 7.5 * mm, doc.report_title[:90])
    canvas.setFillColor(SLATE)
    canvas.drawString(18 * mm, 9 * mm, doc.labels["research_only"])
    page_label = f"{doc.labels['page']} {doc.page}" if doc.labels["page"] == "Page" else f"{doc.labels['page']} {doc.page} 页"
    canvas.drawRightString(width - 18 * mm, 9 * mm, page_label)
    canvas.restoreState()


def _table(rows: list[list[object]], style: dict[str, ParagraphStyle], widths=None) -> Table:
    header_style = ParagraphStyle("TableHeader", parent=style["table"], textColor=colors.white)
    cells = [
        [Paragraph(_text(value), header_style if row_index == 0 else style["table"]) for value in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("FONTNAME", (0, 0), (-1, -1), "ResearchSans"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B9C4CE")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, PALE)),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build(
    payload: dict,
    output: Path,
    sans_path: Path | None,
    serif_path: Path | None,
    sans_index: int | None,
    serif_index: int | None,
) -> None:
    report_text = json.dumps(payload, ensure_ascii=False)
    labels = dict(ZH_LABELS if any("\u4e00" <= character <= "\u9fff" for character in report_text) else EN_LABELS)
    labels.update(payload.get("labels", {}))
    required_codepoints = {ord(character) for character in report_text if not character.isspace()}
    sans, serif = _register_fonts(sans_path, serif_path, sans_index, serif_index, required_codepoints)
    style = _styles(sans, serif)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=17 * mm,
        title=str(payload.get("title", "Strategy Research Report")),
        author="",
        subject="Single-instrument strategy research",
    )
    doc.report_title = str(payload.get("title", "Strategy Research Report"))
    doc.labels = labels
    story = [Spacer(1, 19 * mm), Paragraph(_text(doc.report_title), style["title"])]
    story.append(Paragraph(_text(payload.get("subtitle", "Validated single-instrument time-series research")), style["subtitle"]))
    identity_rows = [[labels["field"], labels["value"]]] + [[key.replace("_", " ").title(), value] for key, value in payload.get("identity", {}).items()]
    if len(identity_rows) > 1:
        story.extend([_table(identity_rows, style, [45 * mm, 115 * mm]), Spacer(1, 8 * mm)])
    story.append(Paragraph(labels["research_only"], style["cover_mark"]))
    story.append(PageBreak())

    story.append(Paragraph(labels["executive_summary"], style["h1"]))
    for paragraph in payload.get("executive_summary", []):
        story.append(Paragraph(_text(paragraph), style["body"]))
    for risk in payload.get("key_risks", []):
        story.append(Paragraph(_text(risk), style["risk"]))

    metrics = payload.get("headline_metrics", [])
    if metrics:
        metric_header = [labels["metric"], labels["train"], labels["validation"], labels["sealed_test"], labels["notes"]]
        story.extend([Paragraph(labels["headline_evidence"], style["h2"]), _table([metric_header] + metrics, style)])

    for section in payload.get("sections", []):
        if section.get("page_break"):
            story.append(PageBreak())
        story.append(Paragraph(_text(section.get("title", "Section")), style["h1"]))
        for paragraph in section.get("paragraphs", []):
            story.append(Paragraph(_text(paragraph), style["body"]))
        if section.get("table"):
            story.append(_table(section["table"], style))
        for chart in section.get("charts", []):
            path = Path(chart["path"])
            if not path.is_file():
                raise SystemExit(f"chart not found: {path}")
            image = Image(str(path))
            image._restrictSize(168 * mm, 110 * mm)
            story.append(KeepTogether([image, Paragraph(_text(chart.get("caption", "")), style["small"]), Spacer(1, 3 * mm)]))

    story.append(PageBreak())
    story.append(Paragraph(labels["reproducibility"], style["h1"]))
    for paragraph in payload.get("disclosures", []):
        story.append(Paragraph(_text(paragraph), style["body"]))
    hashes = payload.get("hashes", {})
    if hashes:
        story.append(_table([[labels["artifact"], labels["checksum"]]] + [[key, value] for key, value in hashes.items()], style, [45 * mm, 115 * mm]))
    class ResearchCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            kwargs["initialFontName"] = "ResearchSans"
            super().__init__(*args, **kwargs)

    doc.build(story, onFirstPage=_page, onLaterPages=_page, canvasmaker=ResearchCanvas)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font-sans", type=Path)
    parser.add_argument("--font-serif", type=Path)
    parser.add_argument("--font-sans-index", type=int)
    parser.add_argument("--font-serif-index", type=int)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build(payload, args.output, args.font_sans, args.font_serif, args.font_sans_index, args.font_serif_index)
    print(json.dumps({"output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
