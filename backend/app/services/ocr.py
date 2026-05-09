import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# Set Tesseract path if needed (Windows default)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

# Threshold: if pdfplumber returns fewer than this many characters of text, we
# treat the PDF as scanned and fall through to image OCR.
_PDFPLUMBER_MIN_CHARS = 80


def process_document(file_path: str) -> str:
    """Process a document (image or PDF) and extract text."""
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            return extract_text_from_image(file_path)
        if ext == '.pdf':
            return extract_text_from_pdf(file_path)
        return f"Unsupported file format: {ext}"
    except Exception as e:
        return f"Error processing document: {str(e)}"


def extract_text_from_image(image_path: str) -> str:
    try:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image)
    except Exception as e:
        msg = str(e).lower()
        if "tesseract is not installed" in msg or "not found" in msg:
            print("Tesseract not found. Returning mock text.")
            return "[MOCK] Tesseract not installed. This is simulated extracted text from the image."
        raise


def _extract_text_with_pdfplumber(pdf_path: str) -> str:
    """Extract text from a digitally-generated PDF without needing OCR.

    Most Form 16s, ITR returns and bank statements arrive as text PDFs
    (reportlab, browser-printed, etc.) and have a real text layer. pdfplumber
    pulls that text without needing Tesseract or Poppler installed.

    Returns an empty string if the PDF is image-only or pdfplumber fails.
    """
    try:
        import pdfplumber  # imported lazily so missing dep doesn't break imports
    except ImportError:
        return ""

    try:
        out = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    out.append(page_text)
        return "\n\n".join(out).strip()
    except Exception:
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF.

    Strategy:
      1. Try pdfplumber (no native binaries required) — works for the vast
         majority of digitally generated Form 16 / ITR PDFs.
      2. If that yields too little text, fall back to pdf2image + Tesseract
         to OCR a scanned PDF.
      3. If both paths fail, return a [MOCK] string so the upload endpoint can
         still respond and the UI can display "OCR unavailable" cleanly.
    """
    text = _extract_text_with_pdfplumber(pdf_path)
    if len(text) >= _PDFPLUMBER_MIN_CHARS:
        return text

    # Scanned / image-only PDF, or pdfplumber missing — try OCR.
    try:
        pages = convert_from_path(pdf_path)
        ocr_text = ""
        for page in pages:
            ocr_text += pytesseract.image_to_string(page) + "\n\n"
        if ocr_text.strip():
            return ocr_text
    except Exception as e:
        msg = str(e).lower()
        # Only swallow the well-known "binaries missing" failures. Real OCR
        # errors (corrupt PDF, etc.) propagate so the API surfaces a 500.
        is_missing_binary = (
            "tesseract is not installed" in msg
            or "not found" in msg
            or "poppler" in msg
        )
        if not is_missing_binary:
            raise

    # If pdfplumber returned *some* text (just below threshold), prefer that
    # over the mock string — partial text is more useful than a placeholder.
    if text:
        return text

    print("OCR tools not found and PDF has no extractable text. Returning mock text.")
    return "[MOCK] OCR tools missing. This is simulated extracted text from the PDF."
