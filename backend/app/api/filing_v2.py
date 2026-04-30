"""FastAPI Router for Indian Tax Filing (LangGraph + tax_engine_in).

Phase 0 endpoints:
  POST /api/v2/calc/preview            - stateless tax computation preview
  POST /api/v2/filing/start            - manual-entry filing path (writes ITR1Filing)
  GET  /api/v2/filing/{id}/pdf         - download generated ITR-1 PDF
  GET  /api/v2/filing/{id}/json        - get ITR-1 JSON in IT Dept schema shape
"""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ITR1Filing, User, Form16
from app.services.tax_engine_in import compute_filing
from app.services.itr1_json_builder import build_itr1_json
from app.services.pdf_generator import generate_itr1_pdf
from app.websockets.manager import manager

router = APIRouter(prefix="/api/v2", tags=["Indian Tax Filing v2"])

PDF_OUTPUT_DIR = Path(os.getenv("ITR_PDF_DIR", "app/uploads/itr1"))
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Calc Preview - stateless tax computation
# ---------------------------------------------------------------------------

class CalcPreviewRequest(BaseModel):
    gross_income: int = Field(ge=0)
    deductions: Dict[str, float] = {}
    regime: Literal["old", "new"]
    is_salary_income: bool = True
    fy: str = "2024-25"


@router.post("/calc/preview")
def calc_preview(req: CalcPreviewRequest):
    """Stateless tax computation preview for the frontend."""
    breakdown = compute_filing(
        gross_income=req.gross_income,
        deductions=req.deductions,
        regime=req.regime,
        is_salary_income=req.is_salary_income,
        fy=req.fy,
    )
    return breakdown.to_dict()


# ---------------------------------------------------------------------------
# Filing Start - manual entry path (Phase 0)
#   Phase 2 will load `salary` and `deductions` from a Form16 row instead.
# ---------------------------------------------------------------------------

class FilingStartRequest(BaseModel):
    """Either provide `form16_id` (Phase 2 path) OR `salary` (manual entry).

    If `form16_id` is supplied, salary and deductions are loaded from the Form16 row.
    `client_id` (optional) routes filing.* progress events back over WebSocket.
    """
    user_id: int
    assessment_year: str = "2025-26"
    regime: Literal["old", "new"]
    form16_id: Optional[int] = None
    salary: Optional[Dict[str, float]] = None     # {"gross": ..., "tds": ...}
    deductions: Optional[Dict[str, float]] = None  # {"80c": ..., "80d": ...}
    client_id: Optional[str] = None                # for WS event routing


class FilingStartResponse(BaseModel):
    filing_id: int
    status: str
    regime: str
    total_tax: int
    tax_due: int
    refund_due: int


async def _emit(client_id: Optional[str], event: str, **payload) -> None:
    """Push a filing.* event to the user's WebSocket channel (best-effort)."""
    if not client_id:
        return
    try:
        await manager.send_to_client(client_id, {"event": event, **payload})
    except Exception:
        pass


@router.post("/filing/start", response_model=FilingStartResponse)
async def start_filing(req: FilingStartRequest, db: Session = Depends(get_db)):
    """Compute a filing from either a Form 16 row or a manual JSON payload."""
    await _emit(req.client_id, "filing.starting", user_id=req.user_id, regime=req.regime)

    user = db.query(User).filter_by(id=req.user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"user {req.user_id} not found")

    # Source the inputs - Form 16 takes precedence over manual entry.
    form16: Optional[Form16] = None
    if req.form16_id is not None:
        form16 = db.query(Form16).filter_by(id=req.form16_id, user_id=req.user_id).one_or_none()
        if not form16:
            raise HTTPException(status_code=404, detail=f"form16 {req.form16_id} not found for user {req.user_id}")
        salary = {
            "gross": float(form16.gross_salary or 0),
            "tds": float(form16.tds_deducted or 0),
        }
        deductions = {
            "80c": float(form16.deductions_80c or 0),
            "80d": float(form16.deductions_80d or 0),
        }
        assessment_year = form16.assessment_year or req.assessment_year
    else:
        if not req.salary:
            raise HTTPException(
                status_code=422,
                detail="Either form16_id or salary must be provided",
            )
        salary = dict(req.salary)
        deductions = dict(req.deductions or {})
        assessment_year = req.assessment_year

    await _emit(req.client_id, "filing.calculating")
    breakdown = compute_filing(
        gross_income=int(salary.get("gross", 0)),
        deductions=deductions,
        regime=req.regime,
        is_salary_income=True,
    )

    user_block = {
        "pan": (form16.employer_pan if form16 else "") or "",
        "aadhaar": None,
        "name": user.full_name or "",
    }

    itr_json = build_itr1_json({
        "user": user_block,
        "assessment_year": assessment_year,
        "regime": req.regime,
        "salary": salary,
        "deductions": deductions,
        "tax_breakdown": breakdown.to_dict(),
    })

    tds_paid = int(salary.get("tds", 0))
    filing = ITR1Filing(
        user_id=req.user_id,
        form16_id=form16.id if form16 else None,
        assessment_year=assessment_year,
        regime=req.regime,
        gross_income=breakdown.gross_income,
        taxable_income=breakdown.taxable_income,
        slab_tax=breakdown.slab_tax,
        rebate_87a=breakdown.rebate_87a,
        surcharge=breakdown.surcharge,
        cess=breakdown.cess,
        total_tax=breakdown.total_tax,
        tds_paid=tds_paid,
        refund_due=max(0, tds_paid - breakdown.total_tax),
        tax_due=max(0, breakdown.total_tax - tds_paid),
        itr1_json=itr_json,
        status="computed",
    )
    db.add(filing)
    db.commit()
    db.refresh(filing)

    # Render & cache the PDF.
    pdf = generate_itr1_pdf({
        "user": user_block,
        "assessment_year": assessment_year,
        "regime": req.regime,
        "salary": salary,
        "deductions": deductions,
        "tax_breakdown": breakdown.to_dict(),
    })
    pdf_path = PDF_OUTPUT_DIR / f"{filing.id}.pdf"
    pdf_path.write_bytes(pdf.getvalue())
    filing.pdf_path = str(pdf_path)
    db.commit()

    await _emit(
        req.client_id,
        "filing.complete",
        filing_id=filing.id,
        regime=filing.regime,
        total_tax=int(filing.total_tax),
        tax_due=int(filing.tax_due),
        refund_due=int(filing.refund_due),
        pdf_url=f"/api/v2/filing/{filing.id}/pdf",
        json_url=f"/api/v2/filing/{filing.id}/json",
    )

    return FilingStartResponse(
        filing_id=filing.id,
        status=filing.status,
        regime=filing.regime,
        total_tax=int(filing.total_tax),
        tax_due=int(filing.tax_due),
        refund_due=int(filing.refund_due),
    )


# ---------------------------------------------------------------------------
# Filing Downloads - PDF and JSON
# ---------------------------------------------------------------------------

@router.get("/filing/{filing_id}/pdf")
def get_filing_pdf(filing_id: int, db: Session = Depends(get_db)):
    filing = db.query(ITR1Filing).filter_by(id=filing_id).one_or_none()
    if not filing or not filing.pdf_path:
        raise HTTPException(status_code=404, detail="filing or PDF not found")
    return FileResponse(
        filing.pdf_path,
        media_type="application/pdf",
        filename=f"itr1-{filing_id}.pdf",
    )


@router.get("/filing/{filing_id}/json")
def get_filing_json(filing_id: int, db: Session = Depends(get_db)):
    filing = db.query(ITR1Filing).filter_by(id=filing_id).one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="filing not found")
    return filing.itr1_json


# ---------------------------------------------------------------------------
# Filing Status
# ---------------------------------------------------------------------------

@router.get("/filing/{filing_id}/status")
def get_filing_status(filing_id: int, db: Session = Depends(get_db)):
    filing = db.query(ITR1Filing).filter_by(id=filing_id).one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="filing not found")
    return {
        "filing_id": filing.id,
        "status": filing.status,
        "regime": filing.regime,
        "assessment_year": filing.assessment_year,
        "total_tax": int(filing.total_tax),
        "tax_due": int(filing.tax_due),
        "refund_due": int(filing.refund_due),
    }


# ---------------------------------------------------------------------------
# Conversational filing flow (LangGraph)
#   Drives the interviewer -> researcher -> calculator -> auditor workflow.
#   Useful when the user prefers a chat-style flow over the structured POST.
# ---------------------------------------------------------------------------

class ChatStartRequest(BaseModel):
    user_id: int
    initial_message: str = "I want to file my ITR-1 for AY 2025-26"


class ChatMessageRequest(BaseModel):
    thread_id: str
    message: str


def _serialize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in messages or []:
        # LangChain messages have .type / .content; raw dicts pass through.
        if hasattr(m, "type") and hasattr(m, "content"):
            out.append({"role": m.type, "content": m.content})
        elif isinstance(m, dict):
            out.append(m)
    return out


def _serialize_result(thread_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "thread_id": thread_id,
        "messages": _serialize_messages(result.get("messages", [])),
        "user_profile": result.get("user_profile"),
        "regime": result.get("regime"),
        "research_results": result.get("research_results"),
        "tax_breakdown": result.get("tax_breakdown") or result.get("calculation_result"),
        "audit_status": result.get("audit_status"),
        "audit_errors": result.get("audit_errors"),
        "current_agent": result.get("current_agent"),
    }


@router.post("/filing/chat/start")
async def chat_start(req: ChatStartRequest):
    """Start a chat-driven filing session via LangGraph."""
    from langchain_core.messages import HumanMessage
    from app.agents_v2.graph import tax_filing_graph
    import uuid as _uuid

    thread_id = f"tax-{req.user_id}-{_uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "messages": [HumanMessage(content=req.initial_message)],
        "thread_id": thread_id,
        "user_profile": {},
        "tax_draft": {},
    }
    try:
        result = await tax_filing_graph.ainvoke(initial_state, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"graph execution failed: {e}")
    return _serialize_result(thread_id, result)


@router.post("/filing/chat/message")
async def chat_message(req: ChatMessageRequest):
    """Continue a chat-driven filing session."""
    from langchain_core.messages import HumanMessage
    from app.agents_v2.graph import tax_filing_graph

    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        snapshot = await tax_filing_graph.aget_state(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to load thread: {e}")
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail=f"thread {req.thread_id} not found")

    updated = {
        **snapshot.values,
        "messages": list(snapshot.values.get("messages", [])) + [HumanMessage(content=req.message)],
    }
    try:
        result = await tax_filing_graph.ainvoke(updated, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"graph execution failed: {e}")
    return _serialize_result(req.thread_id, result)
