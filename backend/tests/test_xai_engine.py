"""
Tests for the XAI (Explainability) engine.

NOTE: The real compute_filing signature is:
    compute_filing(gross_income, deductions, regime, is_salary_income=True, fy="2024-25")
where `deductions` is a dict like {"80c": 150000}.

These tests mirror the plan assertions but use the actual API.
"""
import pytest


def test_explain_breakdown_returns_line_explanations():
    from app.services.xai_engine import explain_breakdown
    from app.services.tax_engine_in import compute_filing

    breakdown = compute_filing(
        gross_income=800_000,
        deductions={"80c": 150_000},
        regime="old",
    )
    result = explain_breakdown(breakdown)
    assert result.regime == "old"
    assert len(result.lines) >= 4
    labels = [l.label for l in result.lines]
    assert "Gross Income" in labels
    assert "Taxable Income" in labels
    assert "Tax (before cess)" in labels
    assert "Tax Payable" in labels


def test_explain_breakdown_has_plain_text():
    from app.services.xai_engine import explain_breakdown
    from app.services.tax_engine_in import compute_filing

    breakdown = compute_filing(
        gross_income=600_000,
        deductions={},
        regime="new",
    )
    result = explain_breakdown(breakdown)
    for line in result.lines:
        assert len(line.explanation) > 10, f"Explanation too short for {line.label}"


def test_what_if_higher_80c_reduces_tax():
    from app.services.xai_engine import what_if
    from app.services.tax_engine_in import compute_filing

    base = compute_filing(
        gross_income=900_000,
        deductions={},
        regime="old",
    )
    result = what_if(base, deductions_80c=150_000)
    assert result.new_tax_payable < result.base_tax_payable
    assert result.tax_saved > 0
    assert "80C" in result.explanation


def test_compare_regimes_returns_both():
    from app.services.xai_engine import compare_regimes
    from app.services.tax_engine_in import compute_filing

    breakdown = compute_filing(
        gross_income=1_200_000,
        deductions={"80c": 150_000},
        regime="old",
    )
    result = compare_regimes(breakdown)
    assert "old" in result
    assert "new" in result
    assert "recommendation" in result
    # tax_payable values exist (may or may not be equal — both outcomes are valid)
    assert result["old"]["tax_payable"] >= 0
    assert result["new"]["tax_payable"] >= 0


def test_rebate_87a_explanation_present_when_applicable():
    from app.services.xai_engine import explain_breakdown
    from app.services.tax_engine_in import compute_filing

    # New regime: 700_000 gross, standard deduction 75_000 -> taxable 625_000
    # which is <= 700_000 threshold, so rebate should apply.
    breakdown = compute_filing(
        gross_income=700_000,
        deductions={},
        regime="new",
    )
    result = explain_breakdown(breakdown)
    labels = [l.label for l in result.lines]
    assert "Rebate u/s 87A" in labels
