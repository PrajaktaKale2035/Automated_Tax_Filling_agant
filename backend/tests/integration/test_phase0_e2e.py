"""End-to-end integration tests for Phase 0."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import User, ITR1Filing


client = TestClient(app)


@pytest.mark.asyncio
async def test_calculator_node_uses_engine_new_regime():
    """LangGraph calculator_node calls compute_filing (no LLM math)."""
    from app.agents_v2.nodes import calculator_node

    state = {
        "messages": [],
        "user_profile": {
            "income_salary": 600_000,
            "deductions_80c": 0,
            "deductions_80d": 0,
            "regime": "new",
        },
        "thread_id": "t-1",
    }
    out = await calculator_node(state)
    assert out["tax_breakdown"]["taxable_income"] == 525_000
    assert out["tax_breakdown"]["total_tax"] == 0
    assert out["regime"] == "new"
    assert out["current_agent"] == "calculator"


@pytest.mark.asyncio
async def test_calculator_node_old_regime_with_80c():
    from app.agents_v2.nodes import calculator_node

    state = {
        "messages": [],
        "user_profile": {
            "income_salary": 1_200_000,
            "deductions_80c": 100_000,
            "deductions_80d": 0,
        },
        "regime": "old",
        "thread_id": "t-2",
    }
    out = await calculator_node(state)
    assert out["tax_breakdown"]["taxable_income"] == 1_050_000
    assert out["tax_breakdown"]["slab_tax"] == 127_500
    assert out["tax_breakdown"]["total_tax"] == 132_600


@pytest.mark.asyncio
async def test_auditor_node_passes_for_valid_breakdown():
    from app.agents_v2.nodes import auditor_node

    state = {
        "tax_breakdown": {
            "gross_income": 600_000,
            "taxable_income": 525_000,
            "slab_tax": 11_250,
            "rebate_87a": 11_250,
            "tax_after_rebate": 0,
            "surcharge": 0,
            "cess": 0,
            "total_tax": 0,
        },
        "thread_id": "t-3",
    }
    out = await auditor_node(state)
    assert out["audit_status"] == "passed"
    assert out["audit_errors"] is None


@pytest.mark.asyncio
async def test_auditor_node_flags_inconsistent_total():
    from app.agents_v2.nodes import auditor_node

    state = {
        "tax_breakdown": {
            "gross_income": 600_000,
            "taxable_income": 525_000,
            "slab_tax": 11_250,
            "rebate_87a": 0,
            "tax_after_rebate": 11_250,
            "surcharge": 0,
            "cess": 450,
            # Wrong: should be 11_700, not 99_999
            "total_tax": 99_999,
        },
        "thread_id": "t-4",
    }
    out = await auditor_node(state)
    assert out["audit_status"] == "failed"
    assert any("total_tax" in e for e in out["audit_errors"])


@pytest.mark.asyncio
async def test_auditor_node_flags_taxable_exceeding_gross():
    from app.agents_v2.nodes import auditor_node

    state = {
        "tax_breakdown": {
            "gross_income": 100_000,
            "taxable_income": 200_000,  # Impossible
            "slab_tax": 0, "rebate_87a": 0, "tax_after_rebate": 0,
            "surcharge": 0, "cess": 0, "total_tax": 0,
        },
        "thread_id": "t-5",
    }
    out = await auditor_node(state)
    assert out["audit_status"] == "failed"
    assert any("exceeds gross" in e for e in out["audit_errors"])


def test_full_phase0_pipeline_via_api(db_session):
    """Full pipeline: POST /start -> DB row -> GET /pdf -> GET /json."""
    user = User(id=99, email="e2e@test.in", hashed_password="x", full_name="E2E User")
    db_session.add(user)
    db_session.commit()

    def _gen():
        yield db_session
    app.dependency_overrides[get_db] = _gen

    try:
        # Start
        resp = client.post("/api/v2/filing/start", json={
            "user_id": 99,
            "regime": "old",
            "salary": {"gross": 1_200_000, "tds": 100_000},
            "deductions": {"80c": 100_000, "80d": 20_000},
        })
        assert resp.status_code == 200, resp.text
        fid = resp.json()["filing_id"]

        # PDF
        pdf = client.get(f"/api/v2/filing/{fid}/pdf")
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        # JSON
        j = client.get(f"/api/v2/filing/{fid}/json")
        assert j.status_code == 200
        body = j.json()
        assert body["formName"] == "ITR-1"
        assert body["taxRegime"] == "old"
        assert body["deductions"]["section80C"] == 100_000

        # DB row
        row = db_session.query(ITR1Filing).filter_by(id=fid).one()
        assert row.status == "computed"
        assert row.pdf_path is not None
        assert row.itr1_json["formName"] == "ITR-1"
    finally:
        app.dependency_overrides.clear()
