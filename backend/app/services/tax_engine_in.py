"""Deterministic Indian tax engine. Pure functions. No LLM calls.

All tax math for ITR-1 (Sahaj) lives here. The LangGraph calculator node and
the /api/v2/calc/preview endpoint both call into this module instead of
asking the LLM to do arithmetic.
"""
from dataclasses import dataclass, asdict
from typing import Literal

from .tax_engine_in_constants import (
    NEW_REGIME_SLABS_FY_2024_25,
    OLD_REGIME_SLABS_FY_2024_25,
    STANDARD_DEDUCTION_NEW_FY_2024_25,
    STANDARD_DEDUCTION_OLD_FY_2024_25,
    REBATE_87A_NEW_FY_2024_25,
    REBATE_87A_OLD_FY_2024_25,
    SURCHARGE_BANDS_FY_2024_25,
    SURCHARGE_BANDS_NEW_FY_2024_25,
    CESS_RATE,
    LIMIT_80C,
    LIMIT_80D_SELF_BELOW_60,
    SUPPORTED_FYS,
)

Regime = Literal["old", "new"]


def _check_fy(fy: str) -> None:
    if fy not in SUPPORTED_FYS:
        raise ValueError(f"unsupported FY: {fy}")


def _slabs_for(regime: Regime, fy: str):
    _check_fy(fy)
    if regime == "new":
        return NEW_REGIME_SLABS_FY_2024_25
    if regime == "old":
        return OLD_REGIME_SLABS_FY_2024_25
    raise ValueError(f"unknown regime: {regime}")


def compute_slab_tax(taxable_income: int, regime: Regime, fy: str = "2024-25") -> int:
    """Apply slab rates to taxable income. Returns tax before rebate/surcharge/cess."""
    if taxable_income <= 0:
        return 0
    slabs = _slabs_for(regime, fy)
    tax = 0.0
    for lower, upper, rate in slabs:
        band_top = upper if upper is not None else taxable_income
        band_size = max(0, min(taxable_income, band_top) - lower)
        if band_size <= 0:
            continue
        tax += band_size * (rate / 100.0)
        if upper is None or taxable_income <= upper:
            break
    return int(round(tax))


def apply_deductions(
    gross_income: int,
    deductions: dict,
    regime: Regime,
    is_salary_income: bool = True,
    fy: str = "2024-25",
) -> int:
    """Subtract permitted deductions from gross income.

    `deductions` is a dict like {"80c": 100_000, "80d": 20_000}. Values that
    exceed statutory limits are capped silently.

    New regime: only standard deduction (Rs 75k). 80C / 80D not allowed.
    Old regime: standard deduction (Rs 50k) + 80C (cap Rs 1.5L) + 80D (cap Rs 25k self <60).
    """
    _check_fy(fy)
    total_deduction = 0
    if is_salary_income:
        total_deduction += (
            STANDARD_DEDUCTION_NEW_FY_2024_25 if regime == "new"
            else STANDARD_DEDUCTION_OLD_FY_2024_25
        )
    if regime == "old":
        d80c = min(int(deductions.get("80c", 0)), LIMIT_80C)
        d80d = min(int(deductions.get("80d", 0)), LIMIT_80D_SELF_BELOW_60)
        total_deduction += d80c + d80d
    return max(0, gross_income - total_deduction)


def apply_rebate_87a(tax: int, total_income: int, regime: Regime, fy: str = "2024-25") -> int:
    """Section 87A rebate. Returns tax after rebate."""
    _check_fy(fy)
    cfg = REBATE_87A_NEW_FY_2024_25 if regime == "new" else REBATE_87A_OLD_FY_2024_25
    if total_income > cfg["income_threshold"]:
        return tax
    rebate = min(tax, cfg["max_rebate"])
    return max(0, tax - rebate)


def compute_surcharge(tax: int, total_income: int, regime: Regime, fy: str = "2024-25") -> int:
    """Surcharge on (tax). New regime caps at 25%."""
    _check_fy(fy)
    bands = SURCHARGE_BANDS_NEW_FY_2024_25 if regime == "new" else SURCHARGE_BANDS_FY_2024_25
    for lower, upper, rate in bands:
        if total_income > lower and (upper is None or total_income <= upper):
            return int(round(tax * rate))
    return 0


def compute_cess(tax: int, surcharge: int) -> int:
    """4% Health & Education Cess on (tax + surcharge)."""
    return int(round((tax + surcharge) * CESS_RATE))


@dataclass(frozen=True)
class TaxBreakdown:
    regime: str
    fy: str
    gross_income: int
    deductions_applied: dict
    taxable_income: int
    slab_tax: int
    rebate_87a: int
    tax_after_rebate: int
    surcharge: int
    cess: int
    total_tax: int

    def to_dict(self) -> dict:
        return asdict(self)


def compute_filing(
    gross_income: int,
    deductions: dict,
    regime: Regime,
    is_salary_income: bool = True,
    fy: str = "2024-25",
) -> TaxBreakdown:
    """Top-level: compute the full tax breakdown for a single filer."""
    taxable = apply_deductions(gross_income, deductions, regime, is_salary_income, fy)
    slab_tax = compute_slab_tax(taxable, regime, fy)
    after_rebate = apply_rebate_87a(slab_tax, taxable, regime, fy)
    rebate_amount = slab_tax - after_rebate
    surcharge = compute_surcharge(after_rebate, taxable, regime, fy)
    cess = compute_cess(after_rebate, surcharge)
    total = after_rebate + surcharge + cess

    return TaxBreakdown(
        regime=regime,
        fy=fy,
        gross_income=int(gross_income),
        deductions_applied=dict(deductions),
        taxable_income=int(taxable),
        slab_tax=int(slab_tax),
        rebate_87a=int(rebate_amount),
        tax_after_rebate=int(after_rebate),
        surcharge=int(surcharge),
        cess=int(cess),
        total_tax=int(total),
    )
