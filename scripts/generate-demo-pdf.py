# scripts/generate-demo-pdf.py — Typeset the two-page synthetic outpatient fixture.
"""Create PDF-01 with ReportLab 5.1.0 and Noto Sans Regular/Bold (SIL OFL 1.1).

Reference: outpatient form 15/BV-01, pages 61–62 of Phụ lục XXVIII,
as cited in docs/plan-nhap-pdf-benh-an.md. The synthetic content comes from
docs/evidence/demo-benh-an-ngoai-tru.txt. Noto Sans source and license:
https://github.com/notofonts/NotoSans

From the repository root on Windows:
uv run --no-project --python 3.11.7 --with reportlab==5.1.0 python scripts/generate-demo-pdf.py
"""

import os
from argparse import ArgumentParser
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/evidence/demo-benh-an-ngoai-tru.txt"
PDF = SOURCE.with_suffix(".pdf")
WIDTH, _ = A4
MARGIN = 51
CONTENT_WIDTH = WIDTH - 2 * MARGIN
INK = HexColor("#18323C")
TEAL = HexColor("#145F62")
QUIET = HexColor("#435D65")
LINE = HexColor("#C6D8DC")
TINT = HexColor("#EEF6F6")


def draw_header(canvas: Canvas, title: str, subtitle: str) -> None:
    """Draw the synthetic marker, heading, and identifying subtitle in reading order."""
    canvas.setFillColor(TINT)
    canvas.roundRect(MARGIN, 765, 146, 24, 5, stroke=0, fill=1)
    canvas.setFont("FixtureBold", 10)
    canvas.setFillColor(TEAL)
    canvas.drawString(MARGIN + 11, 773, "DỮ LIỆU GIẢ LẬP")
    canvas.setFillColor(INK)
    canvas.setFont("FixtureBold", 29)
    canvas.drawString(MARGIN, 718, title)
    canvas.setFillColor(QUIET)
    canvas.setFont("FixtureRegular", 11)
    canvas.drawString(MARGIN, 691, subtitle)
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 672, WIDTH - MARGIN, 672)


def draw_section(canvas: Canvas, top: float, title: str, lines: list[str]) -> float:
    """Draw one section with a selectable text line per source line and return the next top."""
    height = 54 + 22 * len(lines)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(MARGIN, top - height, CONTENT_WIDTH, height, 8, stroke=1, fill=0)
    canvas.setFillColor(TEAL)
    canvas.setFont("FixtureBold", 12)
    canvas.drawString(MARGIN + 18, top - 24, title)
    canvas.setFillColor(INK)
    canvas.setFont("FixtureRegular", 12)
    for index, line in enumerate(lines):
        canvas.drawString(MARGIN + 18, top - 51 - 22 * index, line)
    return top - height - 16


def finish_page(canvas: Canvas, number: int) -> None:
    """Add an unobtrusive page number and close the current page."""
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 66, WIDTH - MARGIN, 66)
    canvas.setFillColor(QUIET)
    canvas.setFont("FixtureRegular", 10)
    canvas.drawRightString(WIDTH - MARGIN, 47, f"Trang {number} / 2")
    canvas.showPage()


def generate_pdf(output: Path, font_dir: Path) -> None:
    """Typeset the source fixture in form order as a deterministic, selectable PDF."""
    for face, filename in (("Regular", "NotoSans-Regular.ttf"), ("Bold", "NotoSans-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(f"Fixture{face}", str(font_dir / filename)))

    source = SOURCE.read_text(encoding="utf-8")
    _, administrative = source.split("I. HÀNH CHÍNH\n", maxsplit=1)
    fields, clinical = administrative.split("II. GHI CHÚ KHÁM\n", maxsplit=1)
    reason, companion, follow_up = clinical.strip().splitlines()
    _, symptoms = reason.split(": ", maxsplit=1)
    missing = "Chưa ghi trong trích đoạn."

    canvas = Canvas(str(output), pagesize=A4, invariant=True, pageCompression=True)
    canvas.setTitle("Bệnh án ngoại trú - Dữ liệu giả lập")
    canvas.setAuthor("MedShield")
    canvas.setSubject("Mẫu học tập PDF-01; bố cục tham chiếu 15/BV-01")

    draw_header(canvas, "BỆNH ÁN NGOẠI TRÚ", "Mã mẫu tham chiếu: 15/BV-01")
    top = draw_section(canvas, 649, "I. HÀNH CHÍNH", fields.strip().splitlines())
    top = draw_section(canvas, top, "II. LÝ DO ĐẾN KHÁM", [reason])
    top = draw_section(canvas, top, "III. HỎI BỆNH", [companion])
    draw_section(canvas, top, "IV. KHÁM BỆNH", [missing])
    finish_page(canvas, 1)

    draw_header(canvas, "TỔNG KẾT BỆNH ÁN", "Tóm tắt ghi chú ngoại trú")
    top = draw_section(canvas, 649, "1. DIỄN BIẾN", [symptoms])
    top = draw_section(canvas, top, "2. KẾT QUẢ KHÁM", [missing])
    draw_section(canvas, top, "3. THEO DÕI", [follow_up])
    finish_page(canvas, 2)
    canvas.save()


def main() -> None:
    """Parse local font/output paths and write the PDF fixture."""
    parser = ArgumentParser(description="Tạo PDF bệnh án ngoại trú giả lập.")
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    parser.add_argument("--font-dir", type=Path, default=fonts)
    parser.add_argument("--output", type=Path, default=PDF)
    args = parser.parse_args()
    generate_pdf(args.output, args.font_dir)


if __name__ == "__main__":
    main()
