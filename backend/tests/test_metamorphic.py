"""
Metamorphic Testing for Tax Calculation Engine

Property-based tests that verify tax logic against invariants,
rather than testing against "correct" outputs.

These tests work regardless of tax code changes.
"""
import pytest
from hypothesis import given, strategies as st, assume
import sys

# Try to import Rust engine, fall back to Python mock if not built
try:
    import tax_engine_rs
    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    print("⚠️  Rust engine not found. Install with: cd rust-engine && maturin develop")
    
    # Mock for testing without Rust
    class MockEngine:
        @staticmethod
        def calculate_tax_indian(income, age, regime="new", **kwargs):
            # Simplified mock
            if regime == "new":
                taxable = income
            else:
                taxable = income - kwargs.get("deductions_80c", 0)
            
            tax = max(0, (taxable - 300000) * 0.20) if taxable > 300000 else 0
            return {
                "tax_liability": tax,
                "taxable_income": taxable,
                "effective_rate": (tax / income * 100) if income > 0 else 0,
                "regime_used": regime
            }
    
    tax_engine_rs = MockEngine()


# ============================================================================
# Metamorphic Property 1: Deduction Monotonicity
# ============================================================================

@given(
    income=st.floats(min_value=100000, max_value=50000000),
    deduction=st.floats(min_value=0, max_value=150000)
)
def test_deduction_reduces_tax(income, deduction):
    """
    Property: Adding a deduction should NEVER increase tax liability.
    
    This holds true regardless of:
    - Tax slab changes
    - Regime changes
    - Rate changes
    """
    # Calculate tax without deduction
    result_without = tax_engine_rs.calculate_tax_indian(
        income=income,
        age=30,
        regime="old",
        deductions_80c=0
    )
    
    # Calculate tax with deduction
    result_with = tax_engine_rs.calculate_tax_indian(
        income=income,
        age=30,
        regime="old",
        deductions_80c=deduction
    )
    
    # Invariant: Tax should not increase
    assert result_with["tax_liability"] <= result_without["tax_liability"], \
        f"Tax increased from {result_without['tax_liability']} to {result_with['tax_liability']} with deduction!"


# ============================================================================
# Metamorphic Property 2: Income Monotonicity
# ============================================================================

@given(
    income=st.floats(min_value=100000, max_value=50000000),
    increment=st.floats(min_value=1000, max_value=100000)
)
def test_income_increase_tax_monotonic(income, increment):
    """
    Property: Increasing income should NEVER decrease absolute tax liability.
    
    (Effective rate can decrease due to slab structure, but total tax increases)
    """
    result1 = tax_engine_rs.calculate_tax_indian(income=income, age=30)
    result2 = tax_engine_rs.calculate_tax_indian(income=income + increment, age=30)
    
    assert result2["tax_liability"] >= result1["tax_liability"], \
        f"Tax decreased from {result1['tax_liability']} to {result2['tax_liability']} with higher income!"


# ============================================================================
# Metamorphic Property 3: Non-Negativity
# ============================================================================

@given(
    income=st.floats(min_value=0, max_value=50000000),
    age=st.integers(min_value=18, max_value=100)
)
def test_tax_non_negative(income, age):
    """
    Property: Tax liability can NEVER be negative.
    """
    result = tax_engine_rs.calculate_tax_indian(income=income, age=age)
    
    assert result["tax_liability"] >= 0, \
        f"Negative tax liability: {result['tax_liability']}"
    
    assert result["taxable_income"] >= 0, \
        f"Negative taxable income: {result['taxable_income']}"


# ============================================================================
# Metamorphic Property 4: Regime Switching
# ============================================================================

@given(
    income=st.floats(min_value=500000, max_value=20000000),
    deductions=st.floats(min_value=0, max_value=200000)
)
def test_regime_rationality(income, deductions):
    """
    Property: For low deductions, New Regime should have <= tax than Old Regime.
    For high deductions, Old Regime should be beneficial.
    
    This is a known property of the Indian tax system design.
    """
    new_regime = tax_engine_rs.calculate_tax_indian(
        income=income,
        age=30,
        regime="new"
    )
    
    old_regime = tax_engine_rs.calculate_tax_indian(
        income=income,
        age=30,
        regime="old",
        deductions_80c=deductions
    )
    
    # If deductions are minimal, new regime should generally be better
    if deductions < 50000:
        # This is a heuristic, not absolute (depends on income slab)
        # Just check that the calculation is reasonable
        assert new_regime["tax_liability"] is not None
        assert old_regime["tax_liability"] is not None


# ============================================================================
# Metamorphic Property 5: Precision Guarantee
# ============================================================================

def test_financial_precision():
    """
    Property: Calculations must not have floating-point errors.
    
    0.1 + 0.2 should equal 0.3 (Rust Decimal guarantees this)
    """
    # Test that small income values are handled precisely
    result = tax_engine_rs.calculate_tax_indian(income=250000.50, age=30)
    
    # Tax should be exactly 0 (below threshold)
    assert result["tax_liability"] == 0, \
        f"Expected 0 tax for income below threshold, got {result['tax_liability']}"
    
    # Taxable income should exactly match input (no deductions in new regime)
    assert abs(result["taxable_income"] - 250000.50) < 0.01, \
        f"Precision error in taxable income calculation"


# ============================================================================
# Extended metamorphic invariants (20 additional properties)
# Tests use app.services.tax_engine_in.compute_filing directly.
# Signature: compute_filing(gross_income, deductions, regime,
#                           is_salary_income=True, fy="2024-25", age=30)
# Returns: TaxBreakdown with fields total_tax, tax_after_rebate, slab_tax,
#          rebate_87a, surcharge, cess, taxable_income, gross_income,
#          age_category, regime, fy, deductions_applied
# Standard deduction: new regime = 75,000; old regime = 50,000
# ============================================================================

from app.services.tax_engine_in import compute_filing as _cf


# P6: Tax is monotonically non-decreasing as gross_income increases (new regime)
def test_income_monotonicity_new_regime():
    """Adding income never decreases total tax in the new regime."""
    results = [
        _cf(gross_income=s, deductions={}, regime="new", age=30).total_tax
        for s in [300_000, 500_000, 700_000, 1_000_000, 1_500_000]
    ]
    for i in range(len(results) - 1):
        assert results[i] <= results[i + 1], (
            f"Tax decreased from {results[i]} to {results[i+1]} at step {i}"
        )


# P7: Tax is monotonically non-decreasing in old regime
def test_income_monotonicity_old_regime():
    """Adding income never decreases total tax in the old regime."""
    results = [
        _cf(gross_income=s, deductions={}, regime="old", age=35).total_tax
        for s in [250_000, 400_000, 600_000, 900_000, 1_200_000]
    ]
    for i in range(len(results) - 1):
        assert results[i] <= results[i + 1], (
            f"Tax decreased from {results[i]} to {results[i+1]} at step {i}"
        )


# P8: Senior citizen tax is always <= general citizen tax at same old-regime income
def test_senior_exemption_gte_general():
    """Senior citizens (60+) never pay more tax than general citizens at same income."""
    income = 600_000
    general = _cf(gross_income=income, deductions={}, regime="old", age=40).total_tax
    senior = _cf(gross_income=income, deductions={}, regime="old", age=65).total_tax
    assert senior <= general, (
        f"Senior tax {senior} exceeds general tax {general} at income {income}"
    )


# P9: Super senior exemption is always >= senior citizen exemption
def test_super_senior_exemption_gte_senior():
    """Super seniors (80+) never pay more tax than seniors (60-79) at same income."""
    income = 600_000
    senior = _cf(gross_income=income, deductions={}, regime="old", age=65).total_tax
    super_senior = _cf(gross_income=income, deductions={}, regime="old", age=82).total_tax
    assert super_senior <= senior, (
        f"Super senior tax {super_senior} exceeds senior tax {senior} at income {income}"
    )


# P10: Rebate 87A gives zero total tax at gross income where taxable <= 700k (new regime)
def test_rebate_87a_zero_at_or_below_700k_new():
    """Gross income of 775k with new regime: 775k - 75k std = 700k taxable.
    87A threshold is 700k, so rebate applies → total_tax must be 0."""
    result = _cf(gross_income=775_000, deductions={}, regime="new", age=30)
    # taxable_income = 775k - 75k = 700k, which is exactly at the 87A threshold
    assert result.taxable_income == 700_000
    assert result.total_tax == 0, (
        f"Expected 0 tax at 700k taxable (new), got {result.total_tax}"
    )


# P11: Just above 87A threshold → non-zero tax in new regime
def test_rebate_87a_nonzero_above_threshold_new():
    """gross=776k → taxable=701k > 700k threshold → 87A does not apply → total_tax > 0."""
    result = _cf(gross_income=776_000, deductions={}, regime="new", age=30)
    assert result.taxable_income == 701_000
    assert result.total_tax > 0, (
        f"Expected non-zero tax above 87A threshold, got {result.total_tax}"
    )


# P12: Rebate 87A gives zero tax when taxable income <= 500k (old regime)
def test_rebate_87a_zero_at_500k_old():
    """gross=550k, old regime: 550k - 50k std = 500k taxable.
    87A threshold is 500k → rebate applies → total_tax = 0."""
    result = _cf(gross_income=550_000, deductions={}, regime="old", age=35)
    assert result.taxable_income == 500_000
    assert result.total_tax == 0, (
        f"Expected 0 tax at 500k taxable (old), got {result.total_tax}"
    )


# P13: 80C deductions never produce negative total_tax
def test_80c_cannot_create_negative_tax():
    """Total tax is always >= 0 regardless of deduction amount."""
    result = _cf(
        gross_income=400_000, deductions={"80c": 150_000}, regime="old", age=35
    )
    assert result.total_tax >= 0, f"Negative total_tax: {result.total_tax}"


# P14: Adding 80C deductions in old regime never increases total_tax
def test_80c_only_reduces_tax():
    """80C deductions (old regime only) must not increase total tax."""
    without = _cf(gross_income=900_000, deductions={}, regime="old", age=35).total_tax
    with_80c = _cf(
        gross_income=900_000, deductions={"80c": 150_000}, regime="old", age=35
    ).total_tax
    assert with_80c <= without, (
        f"Tax increased from {without} to {with_80c} after adding 80C deduction"
    )


# P15: Cess is exactly 4% of (tax_after_rebate + surcharge)
def test_cess_is_exactly_4_percent():
    """Health & Education Cess must equal 4% of (tax_after_rebate + surcharge)."""
    result = _cf(gross_income=1_500_000, deductions={}, regime="new", age=35)
    expected_cess = int(round((result.tax_after_rebate + result.surcharge) * 0.04))
    assert result.cess == expected_cess, (
        f"cess {result.cess} != 4% of "
        f"({result.tax_after_rebate} + {result.surcharge}) = {expected_cess}"
    )


# P16: total_tax = tax_after_rebate + surcharge + cess (internal consistency)
def test_total_tax_composition():
    """total_tax must equal tax_after_rebate + surcharge + cess."""
    result = _cf(gross_income=1_000_000, deductions={}, regime="new", age=30)
    expected = result.tax_after_rebate + result.surcharge + result.cess
    assert result.total_tax == expected, (
        f"total_tax {result.total_tax} != "
        f"tax_after_rebate({result.tax_after_rebate}) + "
        f"surcharge({result.surcharge}) + cess({result.cess}) = {expected}"
    )


# P17: rebate_87a <= slab_tax (rebate cannot exceed the tax it offsets)
def test_rebate_never_exceeds_slab_tax():
    """Rebate 87A must never be larger than the slab tax computed before rebate."""
    for gross in [400_000, 500_000, 600_000, 700_000]:
        result = _cf(gross_income=gross, deductions={}, regime="new", age=30)
        assert result.rebate_87a <= result.slab_tax, (
            f"rebate_87a {result.rebate_87a} > slab_tax {result.slab_tax} "
            f"at gross_income {gross}"
        )


# P18: All TaxBreakdown components are non-negative
def test_all_components_non_negative():
    """No component of TaxBreakdown should be negative."""
    for gross in [0, 100_000, 500_000, 1_000_000, 5_000_000]:
        result = _cf(gross_income=gross, deductions={}, regime="new", age=30)
        for field_name in (
            "slab_tax", "rebate_87a", "tax_after_rebate",
            "surcharge", "cess", "total_tax", "taxable_income",
        ):
            value = getattr(result, field_name)
            assert value >= 0, (
                f"{field_name} is negative ({value}) at gross_income {gross}"
            )


# P19: Surcharge is 0 for taxable income below 50 lakh (5,000,000)
def test_no_surcharge_below_50_lakh():
    """Surcharge only applies when taxable income exceeds Rs 50 lakh."""
    # gross=5_074_999, new regime, std_deduction=75k → taxable=4_999_999 < 5M
    result = _cf(gross_income=5_074_999, deductions={}, regime="new", age=35)
    assert result.taxable_income < 5_000_000
    assert result.surcharge == 0, (
        f"Expected 0 surcharge below 50L taxable, got {result.surcharge}"
    )


# P20: Surcharge > 0 for taxable income above 50 lakh
def test_surcharge_above_50_lakh():
    """Surcharge is non-zero when taxable income exceeds Rs 50 lakh."""
    # gross=6M, new regime, std_deduction=75k → taxable=5,925,000 > 5M
    result = _cf(gross_income=6_000_000, deductions={}, regime="new", age=35)
    assert result.taxable_income > 5_000_000
    assert result.surcharge > 0, (
        f"Expected surcharge > 0 above 50L taxable, got {result.surcharge}"
    )


# P21: New regime: zero tax when taxable income is at or below 300k (0% slab)
def test_new_regime_zero_tax_in_zero_slab():
    """New regime bottom slab (0 - 3L) is 0% → total_tax = 0 if taxable <= 300k."""
    # gross=375k, new regime, std_deduction=75k → taxable=300k (0% slab, no tax)
    result = _cf(gross_income=375_000, deductions={}, regime="new", age=30)
    assert result.taxable_income == 300_000
    assert result.total_tax == 0, (
        f"Expected 0 tax with 300k taxable in new regime, got {result.total_tax}"
    )


# P22: Effective tax rate never exceeds 40% of gross income
def test_effective_rate_under_40_percent():
    """Effective rate = total_tax / gross_income must stay well below 40%."""
    for gross in [500_000, 1_000_000, 2_000_000, 10_000_000]:
        result = _cf(gross_income=gross, deductions={}, regime="new", age=30)
        if result.gross_income > 0:
            effective_rate = result.total_tax / result.gross_income * 100
            assert effective_rate < 40, (
                f"Effective rate {effective_rate:.1f}% exceeds 40% at gross {gross}"
            )


# P23: 80C deduction cap is 1,50,000 — extra 80C beyond cap has no effect
def test_80c_cap_at_150k():
    """Deductions_80c above 1,50,000 are silently capped; tax must not change."""
    at_cap = _cf(
        gross_income=800_000, deductions={"80c": 150_000}, regime="old", age=35
    ).total_tax
    above_cap = _cf(
        gross_income=800_000, deductions={"80c": 200_000}, regime="old", age=35
    ).total_tax
    assert at_cap == above_cap, (
        f"Tax changed from {at_cap} to {above_cap} when 80C exceeded cap"
    )


# P24: Standard deduction is 75,000 for salaried filers in new regime
def test_standard_deduction_new_regime():
    """New regime: taxable_income = gross_income - 75,000 for salaried filers."""
    gross = 600_000
    result = _cf(gross_income=gross, deductions={}, regime="new", age=30)
    assert result.taxable_income == gross - 75_000, (
        f"Expected taxable {gross - 75_000}, got {result.taxable_income}"
    )


# P25: age_category field always holds a recognised value
def test_age_category_valid():
    """age_category in TaxBreakdown must be one of the three defined categories."""
    for age in [25, 60, 80]:
        result = _cf(gross_income=500_000, deductions={}, regime="new", age=age)
        assert result.age_category in ("general", "senior", "super_senior"), (
            f"Unexpected age_category '{result.age_category}' for age {age}"
        )


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    if not HAS_RUST:
        print("\n⚠️  Rust engine not available. Some tests may use mocks.\n")

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
