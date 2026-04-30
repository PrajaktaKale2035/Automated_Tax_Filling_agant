import pytest
from app.services.itr1_json_builder import build_itr1_json


def test_build_itr1_minimum_payload():
    payload = {
        "user": {"pan": "ABCDE1234F", "aadhaar": "123412341234", "name": "Asha Verma"},
        "assessment_year": "2025-26",
        "regime": "new",
        "salary": {"gross": 600_000, "tds": 0},
        "deductions": {},
        "tax_breakdown": {
            "taxable_income": 525_000,
            "slab_tax": 11_250,
            "rebate_87a": 11_250,
            "surcharge": 0,
            "cess": 0,
            "total_tax": 0,
        },
    }
    out = build_itr1_json(payload)
    assert out["formName"] == "ITR-1"
    assert out["assessmentYear"] == "2025-26"
    assert out["personalInfo"]["panNumber"] == "ABCDE1234F"
    assert out["taxComputation"]["totalTaxLiability"] == 0
    assert out["taxRegime"] == "new"


def test_build_itr1_old_regime_with_deductions():
    payload = {
        "user": {"pan": "ABCDE1234F", "aadhaar": "123412341234", "name": "Asha Verma"},
        "assessment_year": "2025-26",
        "regime": "old",
        "salary": {"gross": 1_200_000, "tds": 100_000},
        "deductions": {"80c": 100_000, "80d": 20_000},
        "tax_breakdown": {
            "taxable_income": 1_050_000,
            "slab_tax": 127_500,
            "rebate_87a": 0,
            "surcharge": 0,
            "cess": 5_100,
            "total_tax": 132_600,
        },
    }
    out = build_itr1_json(payload)
    assert out["deductions"]["section80C"] == 100_000
    assert out["deductions"]["section80D"] == 20_000
    assert out["taxComputation"]["totalTaxLiability"] == 132_600
    assert out["taxesPaid"]["tdsTotal"] == 100_000


def test_build_itr1_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="missing"):
        build_itr1_json({"user": {}})
