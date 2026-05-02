"""Tests for the deterministic Indian tax engine.

Source for expected values: Income Tax Act 1961 + Finance Act 2024
(applicable for AY 2025-26 / FY 2024-25). Numbers cross-checked against the
IT Department's official tax calculator.
"""
import pytest

from app.services.tax_engine_in import (
    compute_slab_tax,
    apply_deductions,
    apply_rebate_87a,
    compute_surcharge,
    compute_cess,
    compute_filing,
    TaxBreakdown,
)


# ---------------------------------------------------------------------------
# compute_slab_tax
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("income,regime,expected", [
    # New regime, FY 2024-25
    (0,         "new", 0),
    (300_000,   "new", 0),       # exactly at first slab end
    (500_000,   "new", 10_000),  # 5% of (5L - 3L) = 10k
    (700_000,   "new", 20_000),  # 5% of 4L
    (1_000_000, "new", 50_000),  # 20k + 10% of 3L
    (1_500_000, "new", 140_000), # 20k + 30k + 30k + 60k
    (2_000_000, "new", 290_000), # +30% of 5L = 150k
    # Old regime
    (0,         "old", 0),
    (250_000,   "old", 0),
    (500_000,   "old", 12_500),
    (1_000_000, "old", 112_500), # 12.5k + 20% of 5L
    (1_500_000, "old", 262_500), # 112.5k + 30% of 5L
])
def test_compute_slab_tax(income, regime, expected):
    assert compute_slab_tax(income, regime, fy="2024-25") == expected


def test_compute_slab_tax_unsupported_fy():
    with pytest.raises(ValueError, match="unsupported FY"):
        compute_slab_tax(500_000, "new", fy="2099-00")


def test_compute_slab_tax_invalid_regime():
    with pytest.raises(ValueError, match="regime"):
        compute_slab_tax(500_000, "futuristic", fy="2024-25")


# ---------------------------------------------------------------------------
# apply_deductions
# ---------------------------------------------------------------------------

def test_apply_deductions_old_regime_with_80c():
    # Gross 12L, 80C 1L, 80D 20k, salary income.
    result = apply_deductions(
        gross_income=1_200_000,
        deductions={"80c": 100_000, "80d": 20_000},
        regime="old",
        is_salary_income=True,
    )
    # Standard 50k + 80C 100k + 80D 20k = 170k -> taxable 1,030,000
    assert result == 1_030_000


def test_apply_deductions_new_regime_ignores_80c():
    result = apply_deductions(
        gross_income=1_200_000,
        deductions={"80c": 150_000, "80d": 25_000},
        regime="new",
        is_salary_income=True,
    )
    assert result == 1_125_000  # 1.2M - 75k standard


def test_apply_deductions_caps_80c_at_limit():
    result = apply_deductions(
        gross_income=2_000_000,
        deductions={"80c": 500_000},
        regime="old",
        is_salary_income=True,
    )
    # 2M - 50k standard - 150k (capped) = 1,800,000
    assert result == 1_800_000


def test_apply_deductions_no_negative_taxable():
    result = apply_deductions(
        gross_income=100_000,
        deductions={"80c": 150_000},
        regime="old",
        is_salary_income=True,
    )
    assert result == 0


# ---------------------------------------------------------------------------
# apply_rebate_87a
# ---------------------------------------------------------------------------

def test_rebate_new_regime_full_eligible():
    assert apply_rebate_87a(tax=20_000, total_income=700_000, regime="new") == 0


def test_rebate_new_regime_above_threshold():
    assert apply_rebate_87a(tax=30_000, total_income=700_001, regime="new") == 30_000


def test_rebate_old_regime_full_eligible():
    assert apply_rebate_87a(tax=10_000, total_income=500_000, regime="old") == 0


def test_rebate_old_regime_above_threshold():
    assert apply_rebate_87a(tax=20_000, total_income=600_000, regime="old") == 20_000


def test_rebate_capped_at_max():
    assert apply_rebate_87a(tax=30_000, total_income=700_000, regime="new") == 5_000


# ---------------------------------------------------------------------------
# compute_surcharge
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("income,regime,tax,expected", [
    (4_000_000,  "new", 800_000,    0),       # below first band
    (6_000_000,  "new", 1_200_000,  120_000), # 10% band
    (12_000_000, "new", 3_000_000,  450_000), # 15% band
    (25_000_000, "new", 7_000_000,  1_750_000), # 25% cap (new regime)
    (60_000_000, "old", 18_000_000, 6_660_000), # 37% top band old regime
])
def test_compute_surcharge(income, regime, tax, expected):
    assert compute_surcharge(tax=tax, total_income=income, regime=regime) == expected


# ---------------------------------------------------------------------------
# compute_cess
# ---------------------------------------------------------------------------

def test_compute_cess():
    assert compute_cess(tax=100_000, surcharge=10_000) == 4_400


# ---------------------------------------------------------------------------
# compute_filing orchestrator
# ---------------------------------------------------------------------------

def test_compute_filing_new_regime_low_income_full_rebate():
    # Salaried, gross Rs 6L, new regime -> standard deduction 75k -> taxable 5.25L
    # Slab tax: (5.25L - 3L) * 5% = 11_250
    # Income (5.25L) <= 7L -> rebate up to 25k -> tax 0
    result = compute_filing(
        gross_income=600_000,
        deductions={},
        regime="new",
        is_salary_income=True,
    )
    assert isinstance(result, TaxBreakdown)
    assert result.taxable_income == 525_000
    assert result.slab_tax == 11_250
    assert result.rebate_87a == 11_250
    assert result.tax_after_rebate == 0
    assert result.surcharge == 0
    assert result.cess == 0
    assert result.total_tax == 0


def test_compute_filing_old_regime_with_80c():
    # Gross 12L, 80C 1L, old regime
    # Deductions: 50k standard + 100k 80C = 150k -> taxable 10.5L
    # Slab tax (old):
    #   0-2.5L: 0
    #   2.5-5L (2.5L): 5% = 12_500
    #   5-10L (5L): 20% = 100_000
    #   10-10.5L (50k): 30% = 15_000
    #   total = 127_500
    # Surcharge 0 (income < 50L), Cess 4% of 127_500 = 5_100
    # Total: 132_600
    result = compute_filing(
        gross_income=1_200_000,
        deductions={"80c": 100_000},
        regime="old",
        is_salary_income=True,
    )
    assert result.taxable_income == 1_050_000
    assert result.slab_tax == 127_500
    assert result.rebate_87a == 0
    assert result.surcharge == 0
    assert result.cess == 5_100
    assert result.total_tax == 132_600


def test_compute_filing_high_income_with_surcharge():
    # New regime, gross 60L, no 80C/80D (new regime)
    # Taxable: 60L - 75k = 59.25L
    # Slab tax (new):
    #   first 3L: 0
    #   3-7L (4L): 5% = 20_000
    #   7-10L (3L): 10% = 30_000
    #   10-12L (2L): 15% = 30_000
    #   12-15L (3L): 20% = 60_000
    #   15L+ (44.25L): 30% = 1_327_500
    #   total = 1_467_500
    # Income 59.25L > 50L -> surcharge band 50L-1Cr = 10% = 146_750
    # Cess 4% of (1_467_500 + 146_750) = 4% of 1_614_250 = 64_570
    # Total: 1_467_500 + 146_750 + 64_570 = 1_678_820
    result = compute_filing(
        gross_income=6_000_000,
        deductions={},
        regime="new",
        is_salary_income=True,
    )
    assert result.taxable_income == 5_925_000
    assert result.slab_tax == 1_467_500
    assert result.surcharge == 146_750
    assert result.cess == 64_570
    assert result.total_tax == 1_678_820


def test_compute_filing_returns_dict_serializable():
    result = compute_filing(
        gross_income=600_000,
        deductions={},
        regime="new",
        is_salary_income=True,
    )
    d = result.to_dict()
    assert d["regime"] == "new"
    assert d["taxable_income"] == 525_000
    assert d["total_tax"] == 0
