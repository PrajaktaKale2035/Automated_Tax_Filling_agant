"""Form 16 (Indian salary TDS certificate) structured extraction.

Phase 2: parses raw OCR text from a Form 16 PDF/image into a strict Pydantic
schema, then writes a `Form16` row. Fields not detected default to 0 / None.
The current implementation uses regex heuristics. A future revision can
fall back to GPT-4 with function-calling for low-confidence extractions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

_FORM16_MARKERS = (
    "form no. 16",
    "form 16",
    "certificate under section 203",
    "tds on salary",
)


def is_form16(raw_text: str) -> bool:
    """Heuristic check: does this OCR text look like a Form 16?"""
    lowered = raw_text.lower()
    return any(marker in lowered for marker in _FORM16_MARKERS)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class Form16Data(BaseModel):
    """Normalized Form 16 fields. All amounts in INR."""

    # Part A - employer & employee identifiers
    employer_name: Optional[str] = None
    employer_tan: Optional[str] = None
    employer_pan: Optional[str] = None
    employee_pan: Optional[str] = None
    assessment_year: str = "2025-26"

    # Part B - income & TDS
    gross_salary: float = 0.0
    exempt_allowances: float = 0.0
    standard_deduction_claimed: float = 0.0
    professional_tax: float = 0.0
    deductions_80c: float = 0.0
    deductions_80d: float = 0.0
    tds_deducted: float = 0.0

    # Confidence flag from extractor.
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

# PAN: 5 letters + 4 digits + 1 letter, surrounded by word boundaries so we
# don't match the digit run inside a PAN as a numeric amount.
_PAN_PATTERN = r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
_TAN_PATTERN = r"\b[A-Z]{4}[0-9]{5}[A-Z]\b"
_AY_PATTERN = r"(20[0-9]{2}\s*[-\u2013/]\s*(?:20)?[0-9]{2})"

# Amount pattern: must have a currency prefix OR at least 4 digits when
# isolated (not surrounded by letters). Excludes section references like
# "u/s 17(1)" and digit runs embedded in PANs/TANs.
_AMOUNT_PATTERN = (
    r"(?:Rs\.?\s*|INR\s*|\u20B9\s*)"            # Rs / INR / Rs symbol
    r"([0-9][0-9,]{2,}\.?[0-9]*)"               # at least 3 more digits/commas
    r"|(?<![A-Za-z0-9])([0-9]{4,}(?:,[0-9]{2,3})*\.?[0-9]*)(?![A-Za-z])"
    # bare number: 4+ digits, NOT touching letters/digits on either side
)


def _to_float(s: str) -> float:
    return float(s.replace(",", "").strip())


def _find_number_after(label: str, text: str, window: int = 200) -> Optional[float]:
    """Find the first qualifying numeric amount after a label, within `window` chars."""
    pattern = re.escape(label) + rf".{{0,{window}}}?(?:{_AMOUNT_PATTERN})"
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        for grp in m.groups():
            if grp:
                try:
                    return _to_float(grp)
                except (ValueError, IndexError):
                    continue
    return None


def extract_form16(raw_text: str) -> Form16Data:
    """Parse raw OCR text into a Form16Data record. Best-effort, no exceptions."""
    if not raw_text:
        return Form16Data(extraction_confidence=0.0)

    found_any = False
    data: dict = {}

    # PAN: try to attribute to employer (deductor) vs employee using nearby
    # keywords. Fall back to "first PAN -> employee, second -> employer" since
    # Form 16 lists the employee first in Part A.
    employer_pan_match = re.search(
        rf"(?:deductor|employer)\b.{{0,80}}?({_PAN_PATTERN})",
        raw_text, flags=re.IGNORECASE | re.DOTALL,
    )
    employee_pan_match = re.search(
        rf"employee\b.{{0,80}}?({_PAN_PATTERN})",
        raw_text, flags=re.IGNORECASE | re.DOTALL,
    )
    if employer_pan_match:
        data["employer_pan"] = employer_pan_match.group(1)
        found_any = True
    if employee_pan_match:
        data["employee_pan"] = employee_pan_match.group(1)
        found_any = True

    # Last-resort fallback: positional PAN list.
    if "employer_pan" not in data or "employee_pan" not in data:
        pans = re.findall(_PAN_PATTERN, raw_text)
        if pans:
            if "employee_pan" not in data:
                data["employee_pan"] = pans[0]
            if "employer_pan" not in data and len(pans) > 1:
                data["employer_pan"] = pans[1]
            found_any = True

    tans = re.findall(_TAN_PATTERN, raw_text)
    if tans:
        data["employer_tan"] = tans[0]
        found_any = True

    # Assessment year (e.g. "2025-26" or "2024-2025").
    m_ay = re.search(_AY_PATTERN, raw_text)
    if m_ay:
        ay = re.sub(r"\s+", "", m_ay.group(1)).replace("/", "-").replace("\u2013", "-")
        # Normalize "2024-2025" -> "2024-25".
        parts = ay.split("-")
        if len(parts) == 2 and len(parts[1]) == 4:
            ay = f"{parts[0]}-{parts[1][-2:]}"
        data["assessment_year"] = ay
        found_any = True

    # Employer name: take the first capitalized line that is not "Form 16".
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("form"):
            continue
        if len(line) > 5 and any(c.isupper() for c in line) and not re.search(r"\d{4}", line):
            data["employer_name"] = line[:120]
            found_any = True
            break

    # Numeric fields - try common labels.
    label_map = {
        "gross_salary":               ["gross salary", "salary u/s 17(1)", "total salary"],
        "exempt_allowances":          ["exempt allowance", "u/s 10", "allowances exempt"],
        "standard_deduction_claimed": ["standard deduction"],
        "professional_tax":           ["professional tax", "tax on employment"],
        "deductions_80c":             ["80c", "section 80c"],
        "deductions_80d":             ["80d", "section 80d"],
        "tds_deducted":               ["tax deducted at source", "tds deducted", "total tds"],
    }
    for field, labels in label_map.items():
        for lbl in labels:
            value = _find_number_after(lbl, raw_text)
            if value is not None:
                data[field] = value
                found_any = True
                break

    # Confidence: rough heuristic based on how many fields we filled.
    filled = sum(1 for k in (
        "employer_pan", "employer_tan", "gross_salary", "tds_deducted",
        "deductions_80c", "deductions_80d",
    ) if k in data and data[k])
    confidence = min(1.0, filled / 4.0)
    data["extraction_confidence"] = round(confidence, 2)

    if not found_any:
        return Form16Data(extraction_confidence=0.0)

    return Form16Data(**data)
