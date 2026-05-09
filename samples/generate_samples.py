"""Generate sample documents for manual testing of the ingestion pipelines.

Run from the repo root:

    backend/venv/Scripts/python.exe samples/generate_samples.py

Outputs (under ./samples/):
  - sample_itr1_ay2024-25.pdf      (rendered via the production ITR-1 renderer)
  - sample_form16_ay2024-25.pdf    (a printable Form 16 the OCR extractor can parse)

The JSON fixtures are checked in alongside this script and are not regenerated.
"""
from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path

# Add backend to sys.path so the production renderer is importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.pdf_generator import generate_itr1_pdf  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer,
)


SAMPLES_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# ITR-1 PDF — uses the production renderer, fed the same payload shape as a
# real filing so the ingestion agent's PDF parser sees realistic input.
# ---------------------------------------------------------------------------

ITR1_PAYLOAD = {
    "user": {
        "name": "Rohit Kumar Sharma",
        "pan": "ABCPS1234F",
        "aadhaar": None,
    },
    "assessment_year": "2024-25",
    "regime": "new",
    "salary": {"gross": 1250000, "tds": 130000},
    "deductions": {"80c": 0, "80d": 0},
    "tax_breakdown": {
        "regime": "new",
        "fy": "2023-24",
        "gross_income": 1250000,
        "taxable_income": 1175000,
        "slab_tax": 122500,
        "rebate_87a": 0,
        "tax_after_rebate": 122500,
        "surcharge": 0,
        "cess": 4900,
        "total_tax": 127400,
    },
}


def write_itr1_pdf() -> Path:
    out = SAMPLES_DIR / "sample_itr1_ay2024-25.pdf"
    pdf: BytesIO = generate_itr1_pdf(ITR1_PAYLOAD)
    out.write_bytes(pdf.getvalue())
    return out


# ---------------------------------------------------------------------------
# Form 16 PDF — labels are spelled the same way the regex extractor looks
# for them (gross salary, standard deduction, 80C, 80D, TDS deducted, etc.)
# so a successful round-trip proves the OCR / Form 16 path still works.
# ---------------------------------------------------------------------------

FORM16_DATA = {
    "employer_name": "Globex Industries Pvt Ltd",
    "employer_pan": "AABCG1234M",
    "employer_tan": "BLRG12345B",
    "employee_name": "Priya R Iyer",
    "employee_pan": "BHFPI9876K",
    "assessment_year": "2024-25",
    "period": "01-Apr-2023 to 31-Mar-2024",
    "gross_salary": 1450000,
    "exempt_allowances": 50000,
    "standard_deduction": 50000,
    "professional_tax": 2400,
    "section_80c": 150000,
    "section_80d": 25000,
    "tds_deducted": 142000,
}


def _rs(n: int) -> str:
    """Indian-grouped rupee formatter."""
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return f"Rs {sign}{s}"
    last3 = s[-3:]
    rest = s[:-3]
    grouped = ""
    while len(rest) > 2:
        grouped = "," + rest[-2:] + grouped
        rest = rest[:-2]
    grouped = rest + grouped
    return f"Rs {sign}{grouped},{last3}"


def write_form16_pdf() -> Path:
    out = SAMPLES_DIR / "sample_form16_ay2024-25.pdf"
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14, spaceAfter=8, alignment=1)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceAfter=6)
    body = styles["BodyText"]

    story = []
    story.append(Paragraph("FORM NO. 16", h1))
    story.append(Paragraph(
        "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on salary",
        body,
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Assessment Year: <b>{FORM16_DATA['assessment_year']}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Period: <b>{FORM16_DATA['period']}</b>",
        body,
    ))
    story.append(Spacer(1, 10))

    # Part A — employer / employee identifiers
    story.append(Paragraph("PART A — Identifiers", h2))
    part_a = [
        ["Name and address of the Employer (Deductor):", FORM16_DATA["employer_name"]],
        ["PAN of the Deductor:", FORM16_DATA["employer_pan"]],
        ["TAN of the Deductor:", FORM16_DATA["employer_tan"]],
        ["Name of the Employee:", FORM16_DATA["employee_name"]],
        ["PAN of the Employee:", FORM16_DATA["employee_pan"]],
    ]
    t = Table(part_a, colWidths=[80 * mm, 90 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Part B — salary, deductions, TDS
    story.append(Paragraph("PART B — Annexure", h2))
    part_b = [
        ["1. Gross Salary u/s 17(1)", _rs(FORM16_DATA["gross_salary"])],
        ["2. Allowances exempt u/s 10", _rs(FORM16_DATA["exempt_allowances"])],
        ["3. Standard Deduction u/s 16(ia)", _rs(FORM16_DATA["standard_deduction"])],
        ["4. Professional Tax u/s 16(iii)", _rs(FORM16_DATA["professional_tax"])],
        ["5. Deductions under Section 80C", _rs(FORM16_DATA["section_80c"])],
        ["6. Deductions under Section 80D", _rs(FORM16_DATA["section_80d"])],
        ["7. Total TDS deducted at source", _rs(FORM16_DATA["tds_deducted"])],
    ]
    t = Table(part_b, colWidths=[110 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>This is a sample / synthetic Form 16 generated for testing the "
        "ingestion agent. All identifiers are fictitious.</i>",
        body,
    ))

    doc.build(story)
    out.write_bytes(buf.getvalue())
    return out


# ---------------------------------------------------------------------------
# Self-test: parse the JSON and PDF samples through their respective extractors
# and print a summary, so we can see at a glance that the round trip works.
# ---------------------------------------------------------------------------

def smoke_test() -> None:
    from app.services.itr_extractor import parse_itr_json, parse_itr_pdf
    from app.services.form16_extractor import is_form16, extract_form16
    from app.services.ocr import extract_text_from_pdf

    print("\n=== SMOKE TEST ===\n")

    for fname in ("sample_itr1_ay2024-25.json", "sample_itr2_ay2024-25.json", "sample_itr4_ay2024-25.json"):
        path = SAMPLES_DIR / fname
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        r = parse_itr_json(payload)
        print(f"[JSON] {fname}")
        print(f"  form_type={r.form_type!r}  AY={r.assessment_year!r}  PAN={r.pan!r}  regime={r.regime!r}")
        print(f"  gross_salary={r.gross_salary}  80C={r.deductions_80c}  80D={r.deductions_80d}  TDS={r.tds_paid}")
        print(f"  taxable_income={r.taxable_income}  total_tax={r.total_tax}  refund_due={r.refund_due}")
        print(f"  confidence={r.extraction_confidence}  status={r.extraction_status}\n")

    itr_pdf = SAMPLES_DIR / "sample_itr1_ay2024-25.pdf"
    if itr_pdf.exists():
        r = parse_itr_pdf(str(itr_pdf))
        print("[PDF] sample_itr1_ay2024-25.pdf")
        print(f"  form_type={r.form_type!r}  AY={r.assessment_year!r}  PAN={r.pan!r}")
        print(f"  gross_salary={r.gross_salary}  taxable_income={r.taxable_income}  total_tax={r.total_tax}")
        print(f"  confidence={r.extraction_confidence}  status={r.extraction_status}\n")

    f16_pdf = SAMPLES_DIR / "sample_form16_ay2024-25.pdf"
    if f16_pdf.exists():
        text = extract_text_from_pdf(str(f16_pdf))
        if text and not text.startswith("[MOCK]"):
            print("[PDF] sample_form16_ay2024-25.pdf")
            print(f"  is_form16={is_form16(text)}")
            d = extract_form16(text)
            print(f"  employer_pan={d.employer_pan}  AY={d.assessment_year}")
            print(f"  gross_salary={d.gross_salary}  80C={d.deductions_80c}  80D={d.deductions_80d}  TDS={d.tds_deducted}")
            print(f"  confidence={d.extraction_confidence}\n")
        else:
            print("[PDF] sample_form16_ay2024-25.pdf -- OCR unavailable (Tesseract/Poppler missing); skipping Form 16 self-test.")
            print("       The PDF still uploads fine to /api/documents/upload -- extraction runs server-side where OCR is configured.\n")


def main() -> None:
    print(f"Samples directory: {SAMPLES_DIR}")
    p1 = write_itr1_pdf()
    print(f"  wrote {p1.name} ({p1.stat().st_size:,} bytes)")
    p2 = write_form16_pdf()
    print(f"  wrote {p2.name} ({p2.stat().st_size:,} bytes)")
    smoke_test()


if __name__ == "__main__":
    main()
