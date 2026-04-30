"""API tests for Phase 0 Indian tax filing endpoints."""
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import User, ITR1Filing


client = TestClient(app)


def _override_db(session):
    def _gen():
        yield session
    app.dependency_overrides[get_db] = _gen


# ---------------------------------------------------------------------------
# /api/v2/calc/preview
# ---------------------------------------------------------------------------

def test_calc_preview_new_regime_low_income_full_rebate():
    resp = client.post("/api/v2/calc/preview", json={
        "gross_income": 600_000,
        "deductions": {},
        "regime": "new",
        "is_salary_income": True,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["taxable_income"] == 525_000
    assert body["total_tax"] == 0
    assert body["regime"] == "new"


def test_calc_preview_old_regime_with_80c():
    resp = client.post("/api/v2/calc/preview", json={
        "gross_income": 1_200_000,
        "deductions": {"80c": 100_000},
        "regime": "old",
        "is_salary_income": True,
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["taxable_income"] == 1_050_000
    assert body["slab_tax"] == 127_500
    assert body["total_tax"] == 132_600


def test_calc_preview_invalid_regime_returns_422():
    resp = client.post("/api/v2/calc/preview", json={
        "gross_income": 600_000,
        "deductions": {},
        "regime": "futuristic",
        "is_salary_income": True,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /api/v2/filing/start (manual entry)
# ---------------------------------------------------------------------------

def test_filing_start_manual_entry_creates_filing(db_session):
    user = User(id=1, email="x@y.in", hashed_password="x", full_name="Asha Verma")
    db_session.add(user)
    db_session.commit()
    _override_db(db_session)
    try:
        resp = client.post("/api/v2/filing/start", json={
            "user_id": 1,
            "regime": "new",
            "salary": {"gross": 600_000, "tds": 0},
            "deductions": {},
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "filing_id" in body
        assert body["status"] == "computed"
        assert body["regime"] == "new"
        assert body["total_tax"] == 0

        row = db_session.query(ITR1Filing).filter_by(id=body["filing_id"]).one()
        assert row.regime == "new"
        assert row.total_tax == 0
        assert row.itr1_json["formName"] == "ITR-1"
        assert row.pdf_path is not None
    finally:
        app.dependency_overrides.clear()


def test_filing_start_unknown_user_returns_404(db_session):
    _override_db(db_session)
    try:
        resp = client.post("/api/v2/filing/start", json={
            "user_id": 99999,
            "regime": "new",
            "salary": {"gross": 600_000, "tds": 0},
            "deductions": {},
        })
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /api/v2/filing/{id}/pdf and /json
# ---------------------------------------------------------------------------

def test_get_filing_pdf_streams_pdf_bytes(db_session):
    user = User(id=2, email="a@b.in", hashed_password="x", full_name="Test")
    db_session.add(user)
    db_session.commit()
    _override_db(db_session)
    try:
        client.post("/api/v2/filing/start", json={
            "user_id": 2, "regime": "new",
            "salary": {"gross": 600_000, "tds": 0}, "deductions": {},
        })
        fid = db_session.query(ITR1Filing).first().id

        resp = client.get(f"/api/v2/filing/{fid}/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"
    finally:
        app.dependency_overrides.clear()


def test_get_filing_json_returns_itr1_payload(db_session):
    user = User(id=3, email="c@d.in", hashed_password="x", full_name="Test")
    db_session.add(user)
    db_session.commit()
    _override_db(db_session)
    try:
        client.post("/api/v2/filing/start", json={
            "user_id": 3, "regime": "new",
            "salary": {"gross": 600_000, "tds": 0}, "deductions": {},
        })
        fid = db_session.query(ITR1Filing).first().id

        resp = client.get(f"/api/v2/filing/{fid}/json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["formName"] == "ITR-1"
        assert body["taxRegime"] == "new"
    finally:
        app.dependency_overrides.clear()


def test_get_filing_pdf_404_on_missing(db_session):
    _override_db(db_session)
    try:
        resp = client.get("/api/v2/filing/9999999/pdf")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
