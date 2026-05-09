# Sample Test Fixtures

Synthetic documents for manually testing the ingestion agents end-to-end. All
identifiers (PAN, Aadhaar, names, employer info) are fictitious.

| File | Path tested | What it exercises |
|------|-------------|-------------------|
| `sample_itr1_ay2024-25.json` | `POST /api/documents/upload-itr` (JSON) | ITR-1 IT-Dept schema parser. Should hit confidence 1.0. |
| `sample_itr2_ay2024-25.json` | `POST /api/documents/upload-itr` (JSON) | ITR-2 (capital gains, house property), old regime. |
| `sample_itr4_ay2024-25.json` | `POST /api/documents/upload-itr` (JSON) | ITR-4 (presumptive 44AD), new regime. |
| `sample_itr1_ay2024-25.pdf` | `POST /api/documents/upload-itr` (PDF) | pdfplumber text PDF extraction. Confidence 1.0 in smoke test. |
| `sample_form16_ay2024-25.pdf` | `POST /api/documents/upload` | Form 16 OCR + regex extractor (needs Tesseract + Poppler installed on the server). |

## Manual test recipe

1. Start the backend (`uvicorn app.main:app` from `backend/`) and the frontend (`vite`).
2. Log in to the UI.
3. Go to **Documents** in the sidebar.
4. **Form 16 path:** drop `sample_form16_ay2024-25.pdf` into the *Drag & drop your tax document* zone. The "Form 16" checklist row should tick green and you'll see extracted fields. Requires Tesseract + Poppler.
5. **Previous-year ITR path:** drop any of the four sample ITR files into the *Upload last year's ITR (PDF or JSON)* zone. Extracted fields should render in a card; click **Use this to start a new filing** to land on `/filing/new` with the wizard pre-filled.
6. Click **Start Filing**. The wizard hydrates from the parsed values.

## Regenerate

```bash
backend/venv/Scripts/python.exe samples/generate_samples.py
```

This rewrites the two PDFs and runs an in-process smoke test that prints the
extracted fields for each sample. The JSON files are checked in directly and
are not regenerated.
