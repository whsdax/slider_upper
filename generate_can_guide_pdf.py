# -*- coding: utf-8 -*-
"""把 CAN-guide.md 渲染成 PDF（reportlab，支持中文/表格/代码块）
用法：python generate_can_guide_pdf.py
输出：CAN通信完全指南.pdf
"""

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, KeepTogether
)

HERE = Path(__file__).parent
SRC = HERE / "CAN-guide.md"
OUTPUT = HERE / "CAN通信完全指南.pdf"

pdfmetrics.registerFont(TTFont("YaHei", r"C:\Windows\Fonts\msyh.ttc"))

S = {
    "title": ParagraphStyle("title", fontName="YaHei", fontSize=20, leading=28,
                            textColor=colors.HexColor("#1e293b"), spaceAfter=10),
    "h1": ParagraphStyle("h1", fontName="YaHei", fontSize=15, leading=21,
                         textColor=colors.HexColor("#5b21b6"), spaceBefore=16, spaceAfter=7),
    "h2": ParagraphStyle("h2", fontName="YaHei", fontSize=12.5, leading=17,
                         textColor=colors.HexColor("#334155"), spaceBefore=11, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="YaHei", fontSize=11, leading=15,
                         textColor=colors.HexColor("#475569"), spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="YaHei", fontSize=9.5, leading=15.5,
                           textColor=colors.HexColor("#1e293b"), spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="YaHei", fontSize=9.5, leading=15,
                             leftIndent=12, spaceAfter=2.5),
    "quote": ParagraphStyle("quote", fontName="YaHei", fontSize=9, leading=14.5,
                            textColor=colors.HexColor("#475569"), leftIndent=10,
                            borderPadding=4, backColor=colors.HexColor("#f1f5f9"), spaceAfter=6),
    "code": ParagraphStyle("code", fontName="YaHei", fontSize=8, leading=12,
                           textColor=colors.HexColor("#1e293b"),
                           leftIndent=0, rightIndent=0, spaceBefore=0, spaceAfter=0),
    "cell": ParagraphStyle("cell", fontName="YaHei", fontSize=8, leading=11.5,
                           textColor=colors.HexColor("#1e293b")),
    "cellhead": ParagraphStyle("cellhead", fontName="YaHei", fontSize=8, leading=11.5,
                               textColor=colors.white),
}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    """markdown 行内格式 → reportlab 富文本标签"""
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="YaHei" color="#b45309">\1</font>', t)
    return t


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build_table(rows):
    header = split_row(rows[0])
    ncols = len(header)
    data = [[Paragraph(inline(c), S["cellhead"]) for c in header]]
    for r in rows[2:]:  # 跳过分隔行
        cells = split_row(r)
        cells += [""] * (ncols - len(cells))
        data.append([Paragraph(inline(c), S["cell"]) for c in cells[:ncols]])
    avail = A4[0] - 30 * mm
    tbl = Table(data, colWidths=[avail / ncols] * ncols, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5b21b6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def build_code_block(text):
    """Preformatted 不渲染 backColor，用 Table 包一层实现浅灰底 + 深色字。"""
    avail = A4[0] - 30 * mm
    pre = Preformatted(text, S["code"])
    tbl = Table([[pre]], colWidths=[avail])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return KeepTogether([tbl, Spacer(1, 6)])


def parse(md_lines):
    story = []
    i = 0
    n = len(md_lines)
    first_h1 = True
    while i < n:
        line = md_lines[i]
        stripped = line.rstrip("\n")

        if stripped.startswith("```"):
            block = []
            i += 1
            while i < n and not md_lines[i].rstrip("\n").startswith("```"):
                block.append(md_lines[i].rstrip("\n"))
                i += 1
            i += 1
            story.append(build_code_block("\n".join(block)))
            continue

        if re.match(r"^\|", stripped):
            rows = []
            while i < n and re.match(r"^\|", md_lines[i].rstrip("\n")):
                rows.append(md_lines[i].rstrip("\n"))
                i += 1
            if len(rows) >= 2:
                story.append(build_table(rows))
                story.append(Spacer(1, 4))
            continue

        if stripped.startswith("# "):
            style = S["title"] if first_h1 else S["h1"]
            first_h1 = False
            story.append(Paragraph(inline(stripped[2:]), style))
        elif stripped.startswith("## "):
            story.append(Paragraph(inline(stripped[3:]), S["h2"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(inline(stripped[4:]), S["h3"]))
        elif stripped.startswith("> "):
            quote = [stripped[2:]]
            while i + 1 < n and md_lines[i + 1].rstrip("\n").startswith(">"):
                i += 1
                quote.append(md_lines[i].rstrip("\n").lstrip("> "))
            story.append(Paragraph(inline(" ".join(q for q in quote if q)), S["quote"]))
        elif re.match(r"^\s*[-*] ", stripped):
            text = re.sub(r"^\s*[-*] ", "", stripped)
            story.append(Paragraph("• " + inline(text), S["bullet"]))
        elif re.match(r"^\s*\d+\. ", stripped):
            story.append(Paragraph(inline(stripped.strip()), S["bullet"]))
        elif stripped.strip() in ("---", "***"):
            story.append(Spacer(1, 6))
        elif stripped.strip():
            story.append(Paragraph(inline(stripped.strip()), S["body"]))
        i += 1
    return story


def main():
    md_lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title="CAN通信完全指南", author="slider_upper",
    )
    doc.build(parse(md_lines))
    print(f"OK -> {OUTPUT}")


if __name__ == "__main__":
    main()
