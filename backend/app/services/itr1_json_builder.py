"""Builds the ITR-1 (Sahaj) JSON payload in the IT Department schema shape.

Phase 0 implements a representative subset of the official schema.
Phase 1 will validate against the IT Dept's published JSON Schema once downloaded.
"""
from typing import Any


REQUIRED_TOP = ("user", "assessment_year", "regime", "salary", "tax_breakdown")


def build_itr1_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Build an ITR-1 JSON document from a normalized payload.

    Required keys: user (with .pan), assessment_year, regime, salary, tax_breakdown.
    Optional: deductions.
    """
    for key in REQUIRED_TOP:
        if key not in payload:
            raise ValueError(f"missing required key: {key}")
    user = payload["user"]
    if "pan" not in user:
        raise ValueError("missing user.pan")

    salary = payload["salary"]
    deductions = payload.get("deductions", {})
    tb = payload["tax_breakdown"]

    return {
        "formName": "ITR-1",
        "assessmentYear": payload["assessment_year"],
        "taxRegime": payload["regime"],
        "personalInfo": {
            "panNumber": user["pan"],
            "aadhaarNumber": user.get("aadhaar"),
            "name": user.get("name"),
        },
        "incomeFromSalary": {
            "grossSalary": salary.get("gross", 0),
        },
        "deductions": {
            "section80C": int(deductions.get("80c", 0)),
            "section80D": int(deductions.get("80d", 0)),
        },
        "taxComputation": {
            "taxableIncome": tb.get("taxable_income", 0),
            "slabTax": tb.get("slab_tax", 0),
            "rebate87A": tb.get("rebate_87a", 0),
            "surcharge": tb.get("surcharge", 0),
            "cess": tb.get("cess", 0),
            "totalTaxLiability": tb.get("total_tax", 0),
        },
        "taxesPaid": {
            "tdsTotal": salary.get("tds", 0),
        },
    }
