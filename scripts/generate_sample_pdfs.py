"""Dev helper that regenerates the demo sample PDFs.

Requires reportlab, which is not part of the runtime dependency set.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "data" / "contracts"

try:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
except Exception:  # pragma: no cover - depends on reportlab build
    pass


def build(source_name: str, target_name: str) -> None:
    source = (CONTRACTS / source_name).read_text(encoding="utf-8")
    title_style = ParagraphStyle("Title", fontName="STSong-Light", fontSize=15, leading=20)
    body_style = ParagraphStyle("Body", fontName="STSong-Light", fontSize=10.5, leading=17)
    paragraphs = []
    for index, line in enumerate(source.splitlines()):
        line = line.strip()
        if not line:
            continue
        style = title_style if index == 0 else body_style
        paragraphs.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), style))
    doc = SimpleDocTemplate(str(CONTRACTS / target_name), pagesize=A4)
    doc.build(paragraphs)
    print(f"generated {target_name}")


if __name__ == "__main__":
    build("sample_high_risk_source.txt", "sample_contract_high_risk.pdf")
    build("sample_low_risk_source.txt", "sample_contract_low_risk.pdf")
