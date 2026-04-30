"""Document upload + OCR endpoint.

Phase 0: AutoGen retired. This endpoint runs Tesseract OCR and returns
the raw text. Phase 2 will add a Form16Extractor service that parses the
raw text into a Form16 row with strict Pydantic validation.
"""
import os
import uuid
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.services.ocr import process_document, UPLOAD_DIR
from app.api.auth import get_current_active_user

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(get_current_active_user),
):
    """Upload a tax document and run OCR.

    Phase 0 returns raw OCR text only. Phase 2 will:
      - Detect document type (Form 16, AIS, etc.)
      - Parse via Form16Extractor (deterministic Pydantic schema)
      - Persist to Form16 table
    """
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        raw_text = process_document(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    return {
        "filename": file.filename,
        "stored_path": file_path,
        "raw_text_preview": (raw_text[:500] + "...") if len(raw_text) > 500 else raw_text,
        "extraction_status": "ocr_only",  # Phase 2 will set this to "extracted" or "review_required"
    }
