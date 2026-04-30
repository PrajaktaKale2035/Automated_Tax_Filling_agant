"""Document upload + OCR + Form 16 extraction.

Phase 0: AutoGen retired; OCR-only stub.
Phase 2: detect Form 16, run structured extraction, persist `Form16` row.
"""
import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_active_user
from app.database import get_db
from app.models import Form16, User
from app.services.form16_extractor import extract_form16, is_form16
from app.services.ocr import process_document, UPLOAD_DIR

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload a tax document, run OCR, detect Form 16, and persist on detection.

    Response shape:
      - filename, stored_path, raw_text_preview always present
      - if Form 16 detected: form16_id, extraction_status='extracted', confidence
      - else: extraction_status='ocr_only'
    """
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    file_ext = os.path.splitext(file.filename or "")[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        raw_text = process_document(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    if is_form16(raw_text):
        form16_data = extract_form16(raw_text)

        if form16_data.extraction_confidence < 0.25:
            return {
                "filename": file.filename,
                "stored_path": file_path,
                "raw_text_preview": raw_text[:500],
                "extraction_status": "review_required",
                "extraction_confidence": form16_data.extraction_confidence,
                "extracted_fields": form16_data.model_dump(),
            }

        form16 = Form16(
            user_id=current_user.id,
            assessment_year=form16_data.assessment_year,
            employer_name=form16_data.employer_name,
            employer_tan=form16_data.employer_tan,
            employer_pan=form16_data.employer_pan,
            gross_salary=form16_data.gross_salary,
            exempt_allowances=form16_data.exempt_allowances,
            standard_deduction_claimed=form16_data.standard_deduction_claimed,
            professional_tax=form16_data.professional_tax,
            deductions_80c=form16_data.deductions_80c,
            deductions_80d=form16_data.deductions_80d,
            tds_deducted=form16_data.tds_deducted,
            raw_ocr_text=raw_text,
            extraction_status="extracted",
        )
        db.add(form16)
        db.commit()
        db.refresh(form16)

        return {
            "filename": file.filename,
            "stored_path": file_path,
            "raw_text_preview": raw_text[:500],
            "extraction_status": "extracted",
            "extraction_confidence": form16_data.extraction_confidence,
            "form16_id": form16.id,
            "extracted_fields": form16_data.model_dump(),
        }

    return {
        "filename": file.filename,
        "stored_path": file_path,
        "raw_text_preview": (raw_text[:500] + "...") if len(raw_text) > 500 else raw_text,
        "extraction_status": "ocr_only",
    }
