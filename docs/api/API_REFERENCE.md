# REST API Reference — Indian Tax Filing System

Live OpenAPI schema: <http://localhost:8000/api/openapi.json>
Interactive docs (Swagger UI): <http://localhost:8000/api/docs>

This document is a curated reference for the Phase 0–4 endpoints. For the full machine-readable schema, use the OpenAPI URL above.

> Frontend agent-store API (Vue / Pinia / LangChain.js client side) is documented in [`AGENT_SYSTEM_SUMMARY.md`](./AGENT_SYSTEM_SUMMARY.md).

---

## Authentication

All endpoints under `/api/v2/*` accept anonymous calls in development. `/api/documents/upload` requires a valid bearer token. `/api/users/*` and `/api/auth/me` require a token.

### `POST /api/auth/register`
Body: `{"email", "password", "full_name?"}`
Returns: `{id, email, full_name, is_active, is_verified, created_at}`. Password rules: min 8 chars, ≥1 digit, ≥1 uppercase.

### `POST /api/auth/login`
Form-urlencoded: `username=<email>&password=<password>`
Returns: `{access_token, token_type: "bearer"}`. Use as `Authorization: Bearer <token>`.

### `GET /api/auth/me`
Returns the current user.

### `POST /api/auth/logout`
Best-effort logout marker.

---

## Indian tax filing v2

### `POST /api/v2/calc/preview`
**Stateless tax computation.** Takes nothing from the DB; returns a fresh `TaxBreakdown` for the given inputs.

Body:
```json
{
  "gross_income": 1200000,
  "deductions": {"80c": 100000, "80d": 20000},
  "regime": "old",
  "is_salary_income": true,
  "fy": "2024-25"
}
```

Response:
```json
{
  "regime": "old",
  "fy": "2024-25",
  "gross_income": 1200000,
  "deductions_applied": {"80c": 100000, "80d": 20000},
  "taxable_income": 1030000,
  "slab_tax": 121500,
  "rebate_87a": 0,
  "tax_after_rebate": 121500,
  "surcharge": 0,
  "cess": 4860,
  "total_tax": 126360
}
```

422 on invalid `regime` (must be `"old"` or `"new"`).

---

### `POST /api/v2/filing/start`
**Compute and persist a filing.** Inputs come from either a `Form16` row or a manual JSON payload. Persists an `ITR1Filing` record, renders the PDF, and (optionally) emits WebSocket progress events to a `client_id`.

Body — manual entry:
```json
{
  "user_id": 1,
  "regime": "old",
  "salary": {"gross": 1200000, "tds": 100000},
  "deductions": {"80c": 100000, "80d": 20000},
  "client_id": "ws-1"
}
```

Body — from a Form 16:
```json
{
  "user_id": 1,
  "regime": "old",
  "form16_id": 7
}
```

Response:
```json
{
  "filing_id": 1,
  "status": "computed",
  "regime": "old",
  "total_tax": 126360,
  "tax_due": 26360,
  "refund_due": 0
}
```

Errors:
- 404 — `user_id` or `form16_id` not found
- 422 — neither `form16_id` nor `salary` supplied

If `client_id` is provided and a WebSocket is connected at `/api/ws/{client_id}`, three events are pushed:
1. `filing.starting` — `{user_id, regime}`
2. `filing.calculating`
3. `filing.complete` — `{filing_id, regime, total_tax, tax_due, refund_due, pdf_url, json_url}`

---

### `GET /api/v2/filing/{filing_id}/pdf`
Streams the cached ITR-1 PDF (`application/pdf`). 404 if the filing or PDF doesn't exist.

### `GET /api/v2/filing/{filing_id}/json`
Returns the ITR-1 JSON in IT Department schema shape:
```json
{
  "formName": "ITR-1",
  "assessmentYear": "2025-26",
  "taxRegime": "old",
  "personalInfo": {"panNumber": "...", "aadhaarNumber": null, "name": "..."},
  "incomeFromSalary": {"grossSalary": 1200000},
  "deductions": {"section80C": 100000, "section80D": 20000},
  "taxComputation": {
    "taxableIncome": 1030000,
    "slabTax": 121500,
    "rebate87A": 0,
    "surcharge": 0,
    "cess": 4860,
    "totalTaxLiability": 126360
  },
  "taxesPaid": {"tdsTotal": 100000}
}
```

### `GET /api/v2/filing/{filing_id}/status`
Quick summary with no PDF / JSON payload:
```json
{
  "filing_id": 1,
  "status": "computed",
  "regime": "old",
  "assessment_year": "2025-26",
  "total_tax": 126360,
  "tax_due": 26360,
  "refund_due": 0
}
```

---

## LangGraph chat workflow

These endpoints drive the full `interviewer → researcher → calculator → auditor` graph. Required: `OPENAI_API_KEY` env variable for the interviewer LLM call.

### `POST /api/v2/filing/chat/start`
Body: `{"user_id", "initial_message?"}`
Creates a thread, runs the graph once, returns the resulting state.

Response:
```json
{
  "thread_id": "tax-1-a1b2c3d4",
  "messages": [{"role": "human", "content": "..."}, {"role": "ai", "content": "..."}],
  "user_profile": {"income_salary": 1200000, "regime": "old", "deductions_80c": 100000},
  "regime": "old",
  "research_results": [{"section": "80C", "description": "...", "source": "tax_rules.txt", "score": 0.71}],
  "tax_breakdown": {...},
  "audit_status": "passed",
  "audit_errors": null,
  "current_agent": "auditor"
}
```

### `POST /api/v2/filing/chat/message`
Body: `{"thread_id", "message"}`
Continues the thread. State is restored from LangGraph's `InMemorySaver` (Phase 0 — does not survive restart).

500 with `graph execution failed:` if `OPENAI_API_KEY` is missing or invalid.

---

## Documents (Form 16)

### `POST /api/documents/upload`
**Authentication required.** Multipart upload.

Behavior:
1. File saved under `backend/app/uploads/`
2. Tesseract OCR extracts raw text (mock fallback if Tesseract not installed)
3. Heuristic detection: is this a Form 16?
4. If yes: regex-based structured extraction → `Form16Data` Pydantic model
5. If `extraction_confidence ≥ 0.25`: writes a `form16` row, status `"extracted"`
6. Else: returns `extraction_status: "review_required"` with extracted fields for the user to correct
7. If not Form 16: returns `extraction_status: "ocr_only"` with raw text preview

Response (extracted Form 16):
```json
{
  "filename": "form16-asha.pdf",
  "stored_path": "...",
  "raw_text_preview": "...",
  "extraction_status": "extracted",
  "extraction_confidence": 0.83,
  "form16_id": 7,
  "extracted_fields": {
    "employer_name": "ACME INDIA TECHNOLOGIES PVT LTD",
    "employer_pan": "ACMEP1234L",
    "employer_tan": "ACME12345C",
    "employee_pan": "ABCDE1234F",
    "assessment_year": "2025-26",
    "gross_salary": 1200000.0,
    "deductions_80c": 150000.0,
    "deductions_80d": 25000.0,
    "tds_deducted": 100000.0,
    ...
  }
}
```

---

## WebSocket

### `/api/ws/{client_id}`
Bi-directional channel. The backend pushes:

- `{event: "connected", client_id}` — on accept
- `{event: "echo", message}` — for inbound text messages (Phase 0 placeholder)
- `{event: "agent_activity", agent, message}` — broadcast from LangGraph nodes
- `{event: "filing.starting", user_id, regime}`
- `{event: "filing.calculating"}`
- `{event: "filing.complete", filing_id, regime, total_tax, tax_due, refund_due, pdf_url, json_url}` — when `client_id` was passed to `/api/v2/filing/start`

Reconnect strategy is on the client. The backend tolerates multiple connections per `client_id` (e.g., two browser tabs).

---

## User profile / SDUI

### `GET /api/users/me`, `GET /api/users/me/profile`, `GET /api/users/{user_id}`, `GET /api/users/`
Standard CRUD. Admin checks for non-self access are TODO.

### `GET /api/sdui/dashboard/{user_id}`
Returns a structured-dynamic-UI dashboard schema for the adaptive frontend. Phase 0 leaves this untouched.

---

## Error model

Validation errors (Pydantic) → `422`:
```json
{
  "detail": [{"type": "missing", "loc": ["body", "regime"], "msg": "Field required"}],
  "message": "Validation error - please check your input"
}
```

Database errors → `500` with detail. Generic exceptions → `500` with `detail: "Internal server error"`.

---

## Curl recipes

```bash
# Indian new-regime ₹6L (full Section 87A rebate)
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":600000,"deductions":{},"regime":"new","is_salary_income":true}'

# Register + log in
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.in","password":"Aa123456","full_name":"Asha Verma"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=asha@example.in&password=Aa123456"

# Compute and persist a filing (manual entry)
curl -X POST http://localhost:8000/api/v2/filing/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"regime":"old","salary":{"gross":1200000,"tds":100000},"deductions":{"80c":100000,"80d":20000}}'

# Download the PDF
curl http://localhost:8000/api/v2/filing/1/pdf -o itr1-1.pdf
```
