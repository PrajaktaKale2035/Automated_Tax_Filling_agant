"""Previous-year ITR (PDF / JSON) ingestion.

Two entry points:

* ``parse_itr_json`` — parse a raw ITR JSON payload (the IT Department's own
  schema produced by the e-filing portal). Handles ITR-1, ITR-2 and ITR-4 by
  reading the ``ITR/<form>`` root and pulling well-known nested keys.
* ``parse_itr_pdf`` — convert a saved ITR acknowledgement / full return PDF
  into text via pdfplumber (fast text PDFs) with a Tesseract OCR fallback for
  scanned PDFs, then run heuristic regexes.

Both return a normalized ``ITRImportData`` Pydantic record so the API layer
doesn't care which path the user used.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.services.ocr import extract_text_from_pdf as _ocr_pdf


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class ITRImportData(BaseModel):
    """Normalized fields shared between PDF and JSON ingestion paths."""

    # Identifiers
    assessment_year: Optional[str] = None
    form_type: Optional[str] = None
    pan: Optional[str] = None
    name: Optional[str] = None
    regime: Optional[str] = None

    # Income
    gross_salary: float = 0.0
    house_property_income: float = 0.0
    capital_gains: float = 0.0
    business_income: float = 0.0
    other_income: float = 0.0

    # Deductions
    deductions_80c: float = 0.0
    deductions_80d: float = 0.0
    deductions_other: float = 0.0

    # Computed
    taxable_income: float = 0.0
    total_tax: float = 0.0
    tds_paid: float = 0.0
    refund_due: float = 0.0
    tax_due: float = 0.0

    # Provenance
    raw_payload: dict = Field(default_factory=dict)
    raw_text: str = ""
    extraction_confidence: float = 0.0
    extraction_status: str = "parsed"  # parsed | review_required | failed


# ---------------------------------------------------------------------------
# JSON path
# ---------------------------------------------------------------------------

# Map of canonical field name -> list of dotted paths to try, ordered by
# preference. Dotted paths support dict keys only (the IT Dept JSON does
# not use array indices at these levels).
_JSON_FIELD_PATHS = {
    "gross_salary": [
        "ITR.ITR1.ITR1_IncomeDeductions.GrossSalary",
        "ITR.ITR2.ScheduleS.TotalGrossSalary",
        "ITR.ITR4.IncomeDeductions.GrossSalary",
        "ITR1_IncomeDeductions.GrossSalary",
        "IncomeDeductions.GrossSalary",
    ],
    "house_property_income": [
        "ITR.ITR1.ITR1_IncomeDeductions.IncomeFromHP",
        "ITR.ITR2.ScheduleHP.TotalIncomeChargeableUnHP",
        "ITR.ITR4.IncomeDeductions.IncomeFromHP",
        "IncomeDeductions.IncomeFromHP",
    ],
    "business_income": [
        "ITR.ITR4.Schedule_BP.PresumptiveBusiness44AD.PresumptiveIncome",
        "ITR.ITR4.IncomeDeductions.IncomeFromBP",
        "Schedule_BP.PresumptiveBusiness44AD.PresumptiveIncome",
    ],
    "other_income": [
        "ITR.ITR1.ITR1_IncomeDeductions.IncomeOthSrc",
        "ITR.ITR2.ScheduleOS.TotIncFromOS",
        "ITR.ITR4.IncomeDeductions.IncomeOthSrc",
        "IncomeDeductions.IncomeOthSrc",
    ],
    "deductions_80c": [
        "ITR.ITR1.ITR1_IncomeDeductions.DeductUndChapVIA.Section80C",
        "ITR.ITR2.ScheduleVIA.DeductUndChapVIA.Section80C",
        "ITR.ITR4.IncomeDeductions.DeductUndChapVIA.Section80C",
        "DeductUndChapVIA.Section80C",
    ],
    "deductions_80d": [
        "ITR.ITR1.ITR1_IncomeDeductions.DeductUndChapVIA.Section80D",
        "ITR.ITR2.ScheduleVIA.DeductUndChapVIA.Section80D",
        "ITR.ITR4.IncomeDeductions.DeductUndChapVIA.Section80D",
        "DeductUndChapVIA.Section80D",
    ],
    "taxable_income": [
        "ITR.ITR1.ITR1_IncomeDeductions.TotalIncome",
        "ITR.ITR2.PartB-TI.TotalIncome",
        "ITR.ITR4.PartB_TI.TotalIncome",
        "PartB_TI.TotalIncome",
    ],
    "total_tax": [
        "ITR.ITR1.ITR1_TaxComputation.TotalTaxPayable",
        "ITR.ITR2.PartB-TTI.ComputationOfTaxLiability.TotalTaxPayable",
        "ITR.ITR4.TaxComputation.TotalTaxPayable",
        "TaxComputation.TotalTaxPayable",
    ],
    "tds_paid": [
        "ITR.ITR1.TaxPaid.TaxesPaid.TDS",
        "ITR.ITR1.TaxPaid.TDS",
        "ITR.ITR2.PartB-TTI.TaxPaid.TaxesPaid.TDS",
        "ITR.ITR2.PartB-TTI.TaxPaid.TDS",
        "ITR.ITR4.TaxPaid.TDS",
        "TaxPaid.TaxesPaid.TDS",
        "TaxPaid.TDS",
    ],
    "refund_due": [
        "ITR.ITR1.Refund.RefundDue",
        "ITR.ITR2.PartB-TTI.Refund.RefundDue",
        "ITR.ITR4.Refund.RefundDue",
    ],
    "pan": [
        "ITR.ITR1.PersonalInfo.PAN",
        "ITR.ITR2.PartA_GEN1.PersonalInfo.PAN",
        "ITR.ITR4.PersonalInfo.PAN",
        "PersonalInfo.PAN",
    ],
    "name": [
        "ITR.ITR1.PersonalInfo.AssesseeName.FirstName",
        "ITR.ITR2.PartA_GEN1.PersonalInfo.AssesseeName.FirstName",
        "ITR.ITR4.PersonalInfo.AssesseeName.FirstName",
        "PersonalInfo.AssesseeName.FirstName",
    ],
    "assessment_year": [
        "ITR.ITR1.Form_ITR1.AssessmentYear",
        "ITR.ITR2.Form_ITR2.AssessmentYear",
        "ITR.ITR4.Form_ITR4.AssessmentYear",
    ],
}


def _dig(payload: dict, dotted: str) -> Any:
    """Walk a dotted key path through nested dicts, returning None on miss."""
    node: Any = payload
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _coerce_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _detect_form_type(payload: dict) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    itr = payload.get("ITR", payload)
    if not isinstance(itr, dict):
        return None
    for k in ("ITR1", "ITR2", "ITR3", "ITR4"):
        if k in itr:
            return f"ITR-{k[-1]}"
    return None


def _detect_regime(payload: dict) -> Optional[str]:
    """Read the OptingNewTaxRegime / TaxRegime flag if present."""
    candidates = [
        "ITR.ITR1.FilingStatus.OptingNewTaxRegime",
        "ITR.ITR2.PartA_GEN1.FilingStatus.OptingNewTaxRegime",
        "ITR.ITR2.FilingStatus.OptingNewTaxRegime",
        "ITR.ITR4.FilingStatus.OptingNewTaxRegime",
        "FilingStatus.OptingNewTaxRegime",
        "ITR.ITR1.FilingStatus.NewTaxRegime",
    ]
    for path in candidates:
        v = _dig(payload, path)
        if v is None:
            continue
        s = str(v).strip().lower()
        if s in ("y", "yes", "true", "1", "n", "no", "false", "0"):
            return "new" if s in ("y", "yes", "true", "1") else "old"
    return None


def parse_itr_json(payload: dict) -> ITRImportData:
    """Parse an IT-Department-shape ITR JSON into normalized fields."""
    if not isinstance(payload, dict):
        return ITRImportData(extraction_status="failed", extraction_confidence=0.0)

    form_type = _detect_form_type(payload)
    data: dict = {"raw_payload": payload, "form_type": form_type}

    filled = 0
    for field, paths in _JSON_FIELD_PATHS.items():
        for p in paths:
            value = _dig(payload, p)
            if value is None:
                continue
            if field in {"pan", "name", "assessment_year"}:
                data[field] = str(value)
            else:
                data[field] = _coerce_float(value)
            filled += 1
            break

    regime = _detect_regime(payload)
    if regime:
        data["regime"] = regime
        filled += 1

    # Approximate confidence: how many fields filled out of ~10 important ones.
    data["extraction_confidence"] = round(min(1.0, filled / 8.0), 2)
    data["extraction_status"] = "parsed" if filled >= 3 else "review_required"
    return ITRImportData(**data)


def parse_itr_json_text(raw: str) -> ITRImportData:
    """Parse a JSON string. Returns failed record if JSON is malformed."""
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return ITRImportData(
            extraction_status="failed",
            extraction_confidence=0.0,
            raw_text=raw[:2000],
        )
    result = parse_itr_json(payload)
    result.raw_text = raw[:2000]
    return result


# ---------------------------------------------------------------------------
# PDF path
# ---------------------------------------------------------------------------

_ITR_FORM_MARKERS = (
    ("ITR-1", ["itr-1", "itr 1", "sahaj", "form itr-1"]),
    ("ITR-2", ["itr-2", "itr 2", "form itr-2"]),
    ("ITR-3", ["itr-3", "itr 3", "form itr-3"]),
    ("ITR-4", ["itr-4", "itr 4", "sugam", "form itr-4"]),
)

_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_AY_RE = re.compile(r"(?:assessment\s*year|a\.?y\.?)\s*[:\-]?\s*(20[0-9]{2}\s*[-/]\s*(?:20)?[0-9]{2})", re.IGNORECASE)
_AMOUNT_RE = (
    r"(?:Rs\.?\s*|INR\s*|\u20B9\s*)?"
    r"([0-9][0-9,]{2,}\.?[0-9]*)"
)


def _pdfplumber_text(path: str) -> str:
    """Best-effort text extraction with pdfplumber. Empty string on failure."""
    try:
        import pdfplumber  # type: ignore
        out: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt:
                    out.append(txt)
        return "\n".join(out)
    except Exception:
        return ""


def _detect_form_type_text(text: str) -> Optional[str]:
    lowered = text.lower()
    for canonical, markers in _ITR_FORM_MARKERS:
        if any(m in lowered for m in markers):
            return canonical
    return None


def _amount_after(text: str, label: str, window: int = 200) -> Optional[float]:
    pattern = re.escape(label) + rf".{{0,{window}}}?{_AMOUNT_RE}"
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    grp = m.group(1)
    try:
        return float(grp.replace(",", ""))
    except ValueError:
        return None


_PDF_LABELS = {
    "gross_salary":           ["gross salary", "salary u/s 17(1)", "income from salary", "total salary"],
    "house_property_income":  ["income from house property", "house property"],
    "capital_gains":          ["capital gains", "income from capital gains"],
    "business_income":        ["profits and gains of business", "business or profession", "presumptive income"],
    "other_income":           ["income from other sources", "other sources"],
    "deductions_80c":         ["section 80c", "80c"],
    "deductions_80d":         ["section 80d", "80d"],
    "taxable_income":         ["total income", "taxable income"],
    "total_tax":              ["total tax payable", "tax payable", "total tax"],
    "tds_paid":               ["total tds", "tds", "tax deducted at source"],
    "refund_due":             ["refund", "amount of refund"],
    "tax_due":                ["balance tax payable", "tax due"],
}


def parse_itr_pdf(file_path: str) -> ITRImportData:
    """Extract text from an ITR PDF and apply heuristic regex parsing."""
    text = _pdfplumber_text(file_path)
    if len(text.strip()) < 50:
        # Scanned PDF — fall back to OCR.
        text = _ocr_pdf(file_path) or ""

    if not text or text.startswith("[MOCK]"):
        return ITRImportData(
            extraction_status="failed",
            extraction_confidence=0.0,
            raw_text=text[:2000],
        )

    data: dict = {"raw_text": text[:5000]}
    filled = 0

    form_type = _detect_form_type_text(text)
    if form_type:
        data["form_type"] = form_type
        filled += 1

    pans = _PAN_RE.findall(text)
    if pans:
        data["pan"] = pans[0]
        filled += 1

    ay = _AY_RE.search(text)
    if ay:
        norm = re.sub(r"\s+", "", ay.group(1)).replace("/", "-")
        parts = norm.split("-")
        if len(parts) == 2 and len(parts[1]) == 4:
            norm = f"{parts[0]}-{parts[1][-2:]}"
        data["assessment_year"] = norm
        filled += 1

    for field, labels in _PDF_LABELS.items():
        for lbl in labels:
            v = _amount_after(text, lbl)
            if v is not None:
                data[field] = v
                filled += 1
                break

    data["extraction_confidence"] = round(min(1.0, filled / 10.0), 2)
    data["extraction_status"] = "parsed" if filled >= 3 else "review_required"
    return ITRImportData(**data)
