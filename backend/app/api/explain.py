"""FastAPI router for XAI (Explainability) endpoints.

Endpoints
---------
POST /api/v2/explain/                 — line-by-line explanation of a tax computation
POST /api/v2/explain/whatif           — counterfactual: what happens if an input changes?
POST /api/v2/explain/regime-compare   — compare old vs new regime for a given income
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

from app.services.tax_engine_in import compute_filing
from app.services.xai_engine import (
    explain_breakdown,
    what_if,
    compare_regimes,
)

router = APIRouter(prefix="/api/v2/explain", tags=["explain"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class FilingInput(BaseModel):
    gross_income: int = Field(ge=0, description="Total gross income in INR")
    deductions: dict[str, float] = Field(
        default={},
        description='Eligible deductions dict, e.g. {"80c": 150000, "80d": 25000}',
    )
    regime: Literal["old", "new"] = "new"
    is_salary_income: bool = True
    fy: str = "2024-25"


class WhatIfInput(FilingInput):
    whatif_deductions_80c: Optional[float] = Field(
        default=None,
        description="What-if 80C deduction amount to test",
    )
    whatif_gross_income: Optional[float] = Field(
        default=None,
        description="What-if gross income to test",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=dict)
def explain(req: FilingInput):
    """Return a plain-language explanation of each tax line item."""
    breakdown = compute_filing(
        gross_income=req.gross_income,
        deductions=req.deductions,
        regime=req.regime,
        is_salary_income=req.is_salary_income,
        fy=req.fy,
    )
    result = explain_breakdown(breakdown)
    return {
        "regime": result.regime,
        "age_category": result.age_category,
        "summary": result.summary,
        "lines": [
            {"label": l.label, "value": l.value, "explanation": l.explanation}
            for l in result.lines
        ],
    }


@router.post("/whatif", response_model=dict)
def explain_whatif(req: WhatIfInput):
    """
    Compute a counterfactual: how would the tax change if an input were different?
    Provide at least one `whatif_` field.
    """
    base = compute_filing(
        gross_income=req.gross_income,
        deductions=req.deductions,
        regime=req.regime,
        is_salary_income=req.is_salary_income,
        fy=req.fy,
    )

    changed: dict = {}
    if req.whatif_deductions_80c is not None:
        changed["deductions_80c"] = req.whatif_deductions_80c
    if req.whatif_gross_income is not None:
        changed["gross_salary"] = req.whatif_gross_income

    if not changed:
        raise HTTPException(status_code=400, detail="Provide at least one whatif_ field.")

    result = what_if(base, **changed)
    return {
        "base_tax_payable": result.base_tax_payable,
        "new_tax_payable": result.new_tax_payable,
        "tax_saved": result.tax_saved,
        "explanation": result.explanation,
        "changed_inputs": result.changed_inputs,
    }


@router.post("/regime-compare", response_model=dict)
def explain_regime_compare(req: FilingInput):
    """Compare old vs new regime and return the recommended one."""
    base = compute_filing(
        gross_income=req.gross_income,
        deductions=req.deductions,
        regime=req.regime,
        is_salary_income=req.is_salary_income,
        fy=req.fy,
    )
    return compare_regimes(base)
