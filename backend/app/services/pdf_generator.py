"""ITR-1 (Sahaj) PDF renderer. Replaces the prior US tax-return generator.

Pure rendering - no tax calculations. All numbers must be pre-computed by
`tax_engine_in`.
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer,
)


def _rs(amount: float) -> str:
    """Format a rupee value with Indian grouping: Rs 12,34,567."""
    n = int(round(amount))
    sign = "-" if n < 0 else ""
    n = abs(n)
    s = str(n)
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


def generate_itr1_pdf(payload: dict) -> BytesIO:
    """Render an ITR-1 PDF from the same payload shape used by build_itr1_json.

    Sections:
      1. Personal Info (PAN, name, AY)
      2. Income from Salary
      3. Deductions
      4. Tax Computation (regime breakdown)
      5. Taxes Paid (TDS)
      6. Net Position
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceAfter=6)

    user = payload["user"]
    salary = payload["salary"]
    ded = payload.get("deductions", {})
    tb = payload["tax_breakdown"]

    elems = [
        Paragraph("ITR-1 (Sahaj) - Tax Computation Summary", h1),
        Paragraph(f"Assessment Year: {payload['assessment_year']}", styles["Normal"]),
        Paragraph(f"Regime: {payload['regime'].upper()}", styles["Normal"]),
        Spacer(1, 6),
        Paragraph("1. Personal Information", h2),
        Table([
            ["Name", user.get("name", "")],
            ["PAN", user.get("pan", "")],
            ["Aadhaar", user.get("aadhaar", "") or "-"],
        ], colWidths=[40*mm, 120*mm]),
        Spacer(1, 8),
        Paragraph("2. Income from Salary", h2),
        Table([
            ["Gross Salary", _rs(salary.get("gross", 0))],
        ], colWidths=[80*mm, 80*mm]),
        Spacer(1, 8),
        Paragraph("3. Deductions", h2),
        Table([
            ["Section 80C", _rs(ded.get("80c", 0))],
            ["Section 80D", _rs(ded.get("80d", 0))],
        ], colWidths=[80*mm, 80*mm]),
        Spacer(1, 8),
        Paragraph("4. Tax Computation", h2),
        Table([
            ["Taxable Income",     _rs(tb["taxable_income"])],
            ["Slab Tax",           _rs(tb["slab_tax"])],
            ["Rebate u/s 87A",     _rs(tb["rebate_87a"])],
            ["Surcharge",          _rs(tb["surcharge"])],
            ["Health & Edu Cess",  _rs(tb["cess"])],
            ["Total Tax Liability", _rs(tb["total_tax"])],
        ], colWidths=[80*mm, 80*mm], style=TableStyle([
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ])),
        Spacer(1, 8),
        Paragraph("5. Taxes Paid (TDS)", h2),
        Table([
            ["TDS Deducted", _rs(salary.get("tds", 0))],
        ], colWidths=[80*mm, 80*mm]),
        Spacer(1, 8),
        Paragraph("6. Net Position", h2),
        Table([
            ["Tax Due (positive) / Refund (negative)",
             _rs(tb["total_tax"] - salary.get("tds", 0))],
        ], colWidths=[120*mm, 40*mm]),
    ]

    doc.build(elems)
    buf.seek(0)
    return buf


# Backwards-compat alias for any caller still importing the old name.
def generate_tax_return_pdf(user_data: dict, tax_data: dict) -> BytesIO:
    """DEPRECATED: kept temporarily to avoid breaking imports during the migration.
    New code should call generate_itr1_pdf with a normalized payload."""
    payload = {
        "user": {
            "pan": user_data.get("pan", ""),
            "aadhaar": user_data.get("aadhaar"),
            "name": user_data.get("name", ""),
        },
        "assessment_year": tax_data.get("assessment_year", "2025-26"),
        "regime": tax_data.get("regime", "new"),
        "salary": {
            "gross": tax_data.get("gross_income", 0),
            "tds": tax_data.get("tds", 0),
        },
        "deductions": tax_data.get("deductions", {}),
        "tax_breakdown": tax_data.get("tax_breakdown", {
            "taxable_income": 0, "slab_tax": 0, "rebate_87a": 0,
            "surcharge": 0, "cess": 0, "total_tax": 0,
        }),
    }
    return generate_itr1_pdf(payload)
