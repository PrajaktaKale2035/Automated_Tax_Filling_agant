"""Senior citizen and age-category tests for the Indian tax engine.

Tests verify that compute_filing correctly applies age-aware slab selection
for the old regime (senior >=60 and super-senior >=80) and that the returned
TaxBreakdown exposes an `age_category` field.
"""
import pytest
from app.services.tax_engine_in import compute_filing, TaxBreakdown


# ---------------------------------------------------------------------------
# Senior citizen slab tests
# ---------------------------------------------------------------------------

def test_senior_citizen_exemption_old_regime():
    """Senior citizen (60-79) gets Rs 3L basic exemption in old regime."""
    result = compute_filing(
        gross_income=300_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=62,
    )
    # Taxable 3L <= senior threshold 3L -> slab tax 0
    assert result.total_tax == 0


def test_super_senior_exemption_old_regime():
    """Super senior (80+) gets Rs 5L basic exemption in old regime."""
    result = compute_filing(
        gross_income=500_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=82,
    )
    # Taxable 5L == super-senior threshold -> slab tax 0
    assert result.total_tax == 0


def test_general_citizen_no_senior_exemption():
    """Age < 60 does not get senior citizen exemption (general 2.5L threshold)."""
    result = compute_filing(
        gross_income=300_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=45,
    )
    # Old regime: 0-2.5L exempt, 2.5-3L (50k) @ 5% = 2500; income 3L <= 5L -> rebate
    # Rebate 87A old: max 12_500, income 3L <= 5L threshold -> full rebate -> total_tax 0
    # BUT slab_tax (2500) <= rebate limit (12500) -> rebate = 2500, total_tax = 0
    # Let's be precise about the rebate: rebate applies if taxable_income <= 500_000
    # taxable_income = 300_000, so rebate applies. slab_tax = 2500 <= 12500, rebate = 2500
    assert result.slab_tax == 2_500
    assert result.rebate_87a == 2_500
    assert result.total_tax == 0


def test_general_citizen_above_rebate_threshold_old_regime():
    """Age < 60, income above rebate threshold — tax is non-zero."""
    result = compute_filing(
        gross_income=600_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=45,
    )
    # Old regime: 0-2.5L=0, 2.5-5L=12500, 5-6L=20000 => slab_tax=32500
    # Income 6L > 5L rebate threshold -> no rebate
    # cess 4% of 32500 = 1300, total = 33800
    assert result.slab_tax == 32_500
    assert result.rebate_87a == 0
    assert result.total_tax == 33_800


def test_senior_citizen_above_basic_exemption_old_regime():
    """Senior citizen (60-79) pays tax on income above Rs 3L threshold."""
    result = compute_filing(
        gross_income=600_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=65,
    )
    # Senior: 0-3L=0, 3-5L (2L) @5%=10000, 5-6L (1L) @20%=20000 => slab_tax=30000
    # Income 6L > rebate threshold 5L -> no rebate
    # cess 4% of 30000 = 1200, total = 31200
    assert result.slab_tax == 30_000
    assert result.total_tax == 31_200


def test_super_senior_above_basic_exemption_old_regime():
    """Super senior (80+) pays tax on income above Rs 5L threshold."""
    result = compute_filing(
        gross_income=700_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=81,
    )
    # Super senior: 0-5L=0, 5-7L (2L) @20%=40000 => slab_tax=40000
    # Income 7L > rebate threshold 5L -> no rebate
    # cess 4% of 40000 = 1600, total = 41600
    assert result.slab_tax == 40_000
    assert result.total_tax == 41_600


# ---------------------------------------------------------------------------
# age_category field tests
# ---------------------------------------------------------------------------

def test_age_category_in_breakdown_senior():
    """TaxBreakdown.age_category == 'senior' for age 60-79."""
    result = compute_filing(
        gross_income=800_000,
        deductions={"80c": 150_000},
        regime="old",
        is_salary_income=True,
        age=65,
    )
    assert isinstance(result, TaxBreakdown)
    assert result.age_category == "senior"


def test_super_senior_age_category():
    """TaxBreakdown.age_category == 'super_senior' for age >= 80."""
    result = compute_filing(
        gross_income=800_000,
        deductions={},
        regime="old",
        is_salary_income=True,
        age=81,
    )
    assert result.age_category == "super_senior"


def test_general_age_category():
    """TaxBreakdown.age_category == 'general' for age < 60."""
    result = compute_filing(
        gross_income=800_000,
        deductions={},
        regime="new",
        is_salary_income=True,
        age=35,
    )
    assert result.age_category == "general"


def test_age_category_boundary_60():
    """Exactly age 60 is classified as 'senior'."""
    result = compute_filing(
        gross_income=500_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=60,
    )
    assert result.age_category == "senior"


def test_age_category_boundary_80():
    """Exactly age 80 is classified as 'super_senior'."""
    result = compute_filing(
        gross_income=500_000,
        deductions={},
        regime="old",
        is_salary_income=False,
        age=80,
    )
    assert result.age_category == "super_senior"


def test_age_category_default_is_general():
    """Default age (not supplied) results in 'general' category."""
    result = compute_filing(
        gross_income=500_000,
        deductions={},
        regime="new",
    )
    assert result.age_category == "general"


def test_new_regime_age_does_not_change_slabs():
    """New regime uses same slabs regardless of age (senior or general)."""
    result_young = compute_filing(
        gross_income=800_000,
        deductions={},
        regime="new",
        is_salary_income=True,
        age=30,
    )
    result_senior = compute_filing(
        gross_income=800_000,
        deductions={},
        regime="new",
        is_salary_income=True,
        age=65,
    )
    # Tax should be identical — new regime has no age differentiation
    assert result_young.slab_tax == result_senior.slab_tax
    assert result_young.total_tax == result_senior.total_tax
    # But age_category differs
    assert result_young.age_category == "general"
    assert result_senior.age_category == "senior"
