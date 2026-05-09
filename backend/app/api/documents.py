"""Document upload + OCR + Form 16 / ITR extraction.

Phase 0: AutoGen retired; OCR-only stub.
Phase 2: detect Form 16, run structured extraction, persist `Form16` row.
Phase 3: dedicated ``/upload-itr`` endpoint for previous-year ITR PDF/JSON
         imports — feeds the ingestion agent so a new filing can be pre-filled.
"""
import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_active_user
from app.database import get_db
from app.models import Form16, ITRImport, User
from app.services.form16_extractor import extract_form16, is_form16
from app.services.itr_extractor import parse_itr_json_text, parse_itr_pdf
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
    user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename or "")[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(user_dir, filename)

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


@router.post("/upload-itr")
async def upload_previous_itr(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload a previous year's ITR (PDF or JSON) and parse it for prefill.

    Accepts ``application/json`` payloads (the IT Department's own ITR JSON
    schema) or a ``.pdf`` (filed acknowledgement / full return).
    """
    user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)

    original_name = file.filename or "itr-upload"
    file_ext = os.path.splitext(original_name)[1].lower()
    if file_ext not in (".pdf", ".json"):
        raise HTTPException(
            status_code=400,
            detail="Only .pdf or .json ITR files are accepted on this endpoint.",
        )

    stored_name = f"{uuid.uuid4()}{file_ext}"
    stored_path = os.path.join(user_dir, stored_name)
    with open(stored_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    if file_ext == ".json":
        try:
            with open(stored_path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Could not read uploaded file: {e}")
        result = parse_itr_json_text(raw)
        source_format = "json"
    else:
        result = parse_itr_pdf(stored_path)
        source_format = "pdf"

    record = ITRImport(
        user_id=current_user.id,
        source_filename=original_name,
        source_format=source_format,
        stored_path=stored_path,
        assessment_year=result.assessment_year,
        form_type=result.form_type,
        pan=result.pan,
        name=result.name,
        regime=result.regime,
        gross_salary=result.gross_salary,
        house_property_income=result.house_property_income,
        capital_gains=result.capital_gains,
        business_income=result.business_income,
        other_income=result.other_income,
        deductions_80c=result.deductions_80c,
        deductions_80d=result.deductions_80d,
        deductions_other=result.deductions_other,
        taxable_income=result.taxable_income,
        total_tax=result.total_tax,
        tds_paid=result.tds_paid,
        refund_due=result.refund_due,
        tax_due=result.tax_due,
        raw_text=result.raw_text,
        parsed_payload=result.raw_payload,
        extraction_status=result.extraction_status,
        extraction_confidence=result.extraction_confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "filename": original_name,
        "source_format": source_format,
        "extraction_status": result.extraction_status,
        "extraction_confidence": result.extraction_confidence,
        "extracted_fields": {
            "assessment_year": result.assessment_year,
            "form_type": result.form_type,
            "pan": result.pan,
            "name": result.name,
            "regime": result.regime,
            "gross_salary": result.gross_salary,
            "house_property_income": result.house_property_income,
            "capital_gains": result.capital_gains,
            "business_income": result.business_income,
            "other_income": result.other_income,
            "deductions_80c": result.deductions_80c,
            "deductions_80d": result.deductions_80d,
            "deductions_other": result.deductions_other,
            "taxable_income": result.taxable_income,
            "total_tax": result.total_tax,
            "tds_paid": result.tds_paid,
            "refund_due": result.refund_due,
            "tax_due": result.tax_due,
        },
    }
