from io import BytesIO
from app.services.pdf_generator import generate_itr1_pdf


SAMPLE_PAYLOAD_NEW_REGIME_LOW = {
    "user": {"pan": "ABCDE1234F", "name": "Asha Verma"},
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


def test_generate_itr1_pdf_returns_bytesio_with_pdf_magic():
    buf = generate_itr1_pdf(SAMPLE_PAYLOAD_NEW_REGIME_LOW)
    assert isinstance(buf, BytesIO)
    data = buf.getvalue()
    assert data[:4] == b"%PDF"
    assert len(data) > 1000


def test_generate_itr1_pdf_old_regime_with_deductions(tmp_path):
    payload = {
        "user": {"pan": "ABCDE1234F", "name": "Test"},
        "assessment_year": "2025-26",
        "regime": "old",
        "salary": {"gross": 1_200_000, "tds": 100_000},
        "deductions": {"80c": 100_000},
        "tax_breakdown": {
            "taxable_income": 1_050_000, "slab_tax": 127_500,
            "rebate_87a": 0, "surcharge": 0, "cess": 5_100, "total_tax": 132_600,
        },
    }
    buf = generate_itr1_pdf(payload)
    out = tmp_path / "out.pdf"
    out.write_bytes(buf.getvalue())
    assert out.stat().st_size > 1000
