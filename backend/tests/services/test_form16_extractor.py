"""Tests for the Form 16 structured extractor."""
from app.services.form16_extractor import extract_form16, is_form16, Form16Data


SAMPLE_FORM16_TEXT = """
FORM NO. 16
PART A
Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on salary

Name and address of the Employer:
ACME INDIA TECHNOLOGIES PVT LTD

Name and PAN of the Employee:
Asha Verma  PAN: ABCDE1234F

PAN of the Deductor: ACMEP1234L
TAN of the Deductor: ACME12345C

Assessment Year: 2025-26

PART B
Gross Salary u/s 17(1): Rs. 1,200,000.00
Allowances exempt u/s 10: Rs. 50,000.00
Standard deduction: Rs. 50,000.00
Professional tax: Rs. 2,400.00
Section 80C: Rs. 1,50,000.00
Section 80D: Rs. 25,000.00
Total TDS deducted: Rs. 100,000.00
"""


def test_is_form16_detects_form16():
    assert is_form16(SAMPLE_FORM16_TEXT) is True


def test_is_form16_rejects_random_text():
    assert is_form16("Hello world, this is not a tax form.") is False


def test_extract_form16_pulls_pan_and_tan():
    data = extract_form16(SAMPLE_FORM16_TEXT)
    assert data.employer_pan == "ACMEP1234L"
    assert data.employer_tan == "ACME12345C"
    # Second PAN in text is the employee's.
    assert data.employee_pan == "ABCDE1234F"


def test_extract_form16_pulls_assessment_year():
    data = extract_form16(SAMPLE_FORM16_TEXT)
    assert data.assessment_year == "2025-26"


def test_extract_form16_pulls_numeric_fields():
    data = extract_form16(SAMPLE_FORM16_TEXT)
    assert data.gross_salary == 1_200_000.0
    assert data.standard_deduction_claimed == 50_000.0
    assert data.professional_tax == 2_400.0
    assert data.deductions_80c == 150_000.0
    assert data.deductions_80d == 25_000.0
    assert data.tds_deducted == 100_000.0


def test_extract_form16_confidence_high_for_complete_form():
    data = extract_form16(SAMPLE_FORM16_TEXT)
    assert data.extraction_confidence >= 0.5


def test_extract_form16_low_confidence_for_empty_text():
    data = extract_form16("")
    assert data.extraction_confidence == 0.0
    assert data.gross_salary == 0.0


def test_extract_form16_returns_form16data_instance():
    data = extract_form16(SAMPLE_FORM16_TEXT)
    assert isinstance(data, Form16Data)
