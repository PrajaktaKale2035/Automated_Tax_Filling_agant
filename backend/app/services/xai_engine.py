"""
Rule-based explainability engine for Indian ITR-1 tax computations.
No ML/SHAP — pure deterministic attribution based on TaxBreakdown fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.tax_engine_in import TaxBreakdown, compute_filing


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LineExplanation:
    label: str
    value: float
    explanation: str


@dataclass
class ExplanationResult:
    regime: str
    age_category: str
    lines: list[LineExplanation]
    summary: str


@dataclass
class CounterfactualResult:
    base_tax_payable: float
    new_tax_payable: float
    tax_saved: float
    explanation: str
    changed_inputs: dict[str, Any]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fmt(amount: float) -> str:
    return f"\u20b9{amount:,.0f}"


def _age_category_from_deductions(b: TaxBreakdown) -> str:
    """
    The real TaxBreakdown does not carry an age field, so we return "general"
    for all filers. Senior / super-senior logic would require the caller to pass
    age explicitly; that is wired up in compare_regimes and what_if via the
    age parameter there.
    """
    return "general"


def _slab_explanation(b: TaxBreakdown) -> str:
    if b.regime == "new":
        return (
            f"Tax computed using new regime slabs "
            f"(0%\u21925%\u219210%\u219215%\u219220%\u219230%) "
            f"on taxable income of {_fmt(b.taxable_income)}. "
            f"Slab tax: {_fmt(b.slab_tax)}."
        )
    return (
        f"Tax computed using old regime slabs "
        f"(0%\u21925%\u219220%\u219230%). "
        f"Basic exemption: \u20b92,50,000. "
        f"Taxable income: {_fmt(b.taxable_income)}. "
        f"Slab tax: {_fmt(b.slab_tax)}."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_breakdown(b: TaxBreakdown) -> ExplanationResult:
    """Return a human-readable line-by-line explanation of a TaxBreakdown."""
    lines: list[LineExplanation] = []
    age_category = _age_category_from_deductions(b)

    # Gross Income
    lines.append(LineExplanation(
        label="Gross Income",
        value=float(b.gross_income),
        explanation=f"Total income from all sources before any deductions: {_fmt(b.gross_income)}.",
    ))

    # Deductions
    d = b.deductions_applied
    if b.regime == "old":
        ded_parts = []
        if d.get("80c", 0):
            ded_parts.append(f"80C: {_fmt(d['80c'])}")
        if d.get("80d", 0):
            ded_parts.append(f"80D: {_fmt(d['80d'])}")
        ded_note = (
            "Standard deduction (\u20b950,000 for salaried)" +
            (f" plus {', '.join(ded_parts)}" if ded_parts else "") +
            " applied under old regime."
        )
    else:
        ded_note = (
            "Standard deduction (\u20b975,000 for salaried) applied under new regime. "
            "80C / 80D deductions are not allowed in new regime."
        )

    # Taxable Income
    lines.append(LineExplanation(
        label="Taxable Income",
        value=float(b.taxable_income),
        explanation=(
            f"{ded_note} "
            f"Taxable income: {_fmt(b.taxable_income)}."
        ),
    ))

    # Tax before cess (= slab_tax in this engine; rebate reduces it to tax_after_rebate)
    lines.append(LineExplanation(
        label="Tax (before cess)",
        value=float(b.slab_tax),
        explanation=_slab_explanation(b),
    ))

    # Rebate u/s 87A
    if b.rebate_87a > 0:
        lines.append(LineExplanation(
            label="Rebate u/s 87A",
            value=float(-b.rebate_87a),
            explanation=(
                f"Your total income is within the rebate threshold, so you qualify for "
                f"Section 87A rebate of {_fmt(b.rebate_87a)}. "
                f"This reduces your tax liability significantly."
            ),
        ))

    # Surcharge
    if b.surcharge > 0:
        lines.append(LineExplanation(
            label="Surcharge",
            value=float(b.surcharge),
            explanation=(
                f"Surcharge applies because your income exceeds \u20b950 lakh. "
                f"Amount: {_fmt(b.surcharge)}."
            ),
        ))

    # Cess
    lines.append(LineExplanation(
        label="Health & Education Cess",
        value=float(b.cess),
        explanation=(
            f"4% Health & Education Cess on (tax after rebate + surcharge) = "
            f"({_fmt(b.tax_after_rebate)} + {_fmt(b.surcharge)}) \u00d7 4% = {_fmt(b.cess)}."
        ),
    ))

    # Tax Payable (total_tax in TaxBreakdown)
    lines.append(LineExplanation(
        label="Tax Payable",
        value=float(b.total_tax),
        explanation=f"Total tax liability (tax after rebate + surcharge + cess): {_fmt(b.total_tax)}.",
    ))

    summary = (
        f"Under the {b.regime} tax regime, your total tax payable is {_fmt(b.total_tax)}."
    )

    return ExplanationResult(
        regime=b.regime,
        age_category=age_category,
        lines=lines,
        summary=summary,
    )


def what_if(base: TaxBreakdown, **changed_inputs) -> CounterfactualResult:
    """
    Compute a counterfactual: what would the tax be if certain inputs changed?

    Supported keys in changed_inputs:
      - deductions_80c: new 80C deduction amount
      - gross_salary: new gross income
    """
    new_gross = int(changed_inputs.get("gross_salary", base.gross_income))
    new_80c = int(changed_inputs.get("deductions_80c", base.deductions_applied.get("80c", 0)))
    new_80d = int(base.deductions_applied.get("80d", 0))

    new_breakdown = compute_filing(
        gross_income=new_gross,
        deductions={"80c": new_80c, "80d": new_80d},
        regime=base.regime,
        is_salary_income=True,
        fy=base.fy,
    )

    tax_saved = base.total_tax - new_breakdown.total_tax

    parts: list[str] = []
    if "deductions_80c" in changed_inputs:
        parts.append(f"Investing {_fmt(changed_inputs['deductions_80c'])} in 80C instruments")
    if "gross_salary" in changed_inputs:
        parts.append(f"Changing gross income to {_fmt(changed_inputs['gross_salary'])}")

    action = ", ".join(parts) or "This change"

    if tax_saved > 0:
        explanation = f"{action} would save you {_fmt(tax_saved)} in tax."
    elif tax_saved < 0:
        explanation = f"{action} would increase your tax by {_fmt(abs(tax_saved))}."
    else:
        explanation = f"{action} would not change your tax liability."

    return CounterfactualResult(
        base_tax_payable=float(base.total_tax),
        new_tax_payable=float(new_breakdown.total_tax),
        tax_saved=float(tax_saved),
        explanation=explanation,
        changed_inputs=changed_inputs,
    )


def compare_regimes(base: TaxBreakdown) -> dict:
    """
    Compare old vs new regime for the same gross income and return a recommendation.
    Uses the base breakdown's gross_income and fy; deductions are ignored for
    the new regime comparison (since 80C etc. don't apply there anyway).
    """
    gross = base.gross_income
    fy = base.fy
    # Use whatever 80c/80d the caller had for the old regime comparison
    deductions = dict(base.deductions_applied)

    old_bd = compute_filing(
        gross_income=gross,
        deductions=deductions,
        regime="old",
        is_salary_income=True,
        fy=fy,
    )
    new_bd = compute_filing(
        gross_income=gross,
        deductions={},
        regime="new",
        is_salary_income=True,
        fy=fy,
    )

    recommended = "new" if new_bd.total_tax <= old_bd.total_tax else "old"
    saving = abs(old_bd.total_tax - new_bd.total_tax)

    reason = (
        f"New regime saves {_fmt(saving)} for this income level."
        if recommended == "new"
        else f"Old regime saves {_fmt(saving)} — beneficial if you have 80C/80D deductions."
    )

    return {
        "old": {
            "tax_payable": old_bd.total_tax,
            "taxable_income": old_bd.taxable_income,
        },
        "new": {
            "tax_payable": new_bd.total_tax,
            "taxable_income": new_bd.taxable_income,
        },
        "recommendation": recommended,
        "saving": saving,
        "recommendation_reason": reason,
    }
