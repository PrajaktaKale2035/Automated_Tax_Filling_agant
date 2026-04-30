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
from app.models import ITR1Filing, User
from app.services.tax_engine_in import compute_filing
from app.services.itr1_json_builder import build_itr1_json
from app.services.pdf_generator import generate_itr1_pdf

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
    user_id: int
    assessment_year: str = "2025-26"
    regime: Literal["old", "new"]
    salary: Dict[str, float]            # {"gross": ..., "tds": ...}
    deductions: Dict[str, float] = {}   # {"80c": ..., "80d": ...}


class FilingStartResponse(BaseModel):
    filing_id: int
    status: str
    regime: str
    total_tax: int
    tax_due: int
    refund_due: int


@router.post("/filing/start", response_model=FilingStartResponse)
def start_filing(req: FilingStartRequest, db: Session = Depends(get_db)):
    """Manual-entry filing path. Computes a filing, persists it, and writes the PDF."""
    # Verify user exists.
    user = db.query(User).filter_by(id=req.user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"user {req.user_id} not found")

    breakdown = compute_filing(
        gross_income=int(req.salary.get("gross", 0)),
        deductions=req.deductions,
        regime=req.regime,
        is_salary_income=True,
    )

    user_block = {
        "pan": "",  # Phase 2 will pull from User.pan_encrypted (decrypted)
        "aadhaar": None,
        "name": user.full_name or "",
    }

    itr_json = build_itr1_json({
        "user": user_block,
        "assessment_year": req.assessment_year,
        "regime": req.regime,
        "salary": req.salary,
        "deductions": req.deductions,
        "tax_breakdown": breakdown.to_dict(),
    })

    tds_paid = int(req.salary.get("tds", 0))
    filing = ITR1Filing(
        user_id=req.user_id,
        assessment_year=req.assessment_year,
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
        "assessment_year": req.assessment_year,
        "regime": req.regime,
        "salary": req.salary,
        "deductions": req.deductions,
        "tax_breakdown": breakdown.to_dict(),
    })
    pdf_path = PDF_OUTPUT_DIR / f"{filing.id}.pdf"
    pdf_path.write_bytes(pdf.getvalue())
    filing.pdf_path = str(pdf_path)
    db.commit()

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
# Filing Status (kept from prior version for backwards compat)
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
