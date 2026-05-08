# REST API Reference — Indian Tax Filing System

Live OpenAPI schema: <http://localhost:8000/api/openapi.json>
Interactive docs (Swagger UI): <http://localhost:8000/api/docs>

This document is a curated reference for all active endpoints. For the full machine-readable schema, use the OpenAPI URL above.

---

## Authentication

All `/api/v2/*` and `/api/users/*` endpoints require a valid `Authorization: Bearer <token>` header. `/api/auth/register`, `/api/auth/login`, and `/api/health` are public.

`POST /api/v2/filing/start` additionally requires the user's `role` to be `filer` or `helper` (enforced by `require_role()` in `api/deps.py`).

### `POST /api/auth/register`
Body: `{"email", "password", "full_name?"}`
Returns: `{id, email, full_name, is_active, created_at}`. Password rules: min 8 chars, ≥1 digit, ≥1 uppercase.

### `POST /api/auth/login`
Form-urlencoded: `username=<email>&password=<password>`
Returns: `{access_token, token_type: "bearer"}`. Use as `Authorization: Bearer <token>`.

### `GET /api/auth/me`
Returns the current user.

### `POST /api/auth/logout`
Best-effort logout marker.

---

## User & profile

### `GET /api/users/me`
Returns the current user's account info.

### `PUT /api/users/me`
Body: `{"full_name?", "email?"}`
Updates account info. Returns the updated user.

### `GET /api/users/me/profile`
Returns preferences: `preferred_mode`, `preferred_regime`, `theme`, `notifications_enabled`.

### `PUT /api/users/me/profile`
Body: `{"preferred_mode?", "preferred_regime?", "theme?", "notifications_enabled?"}`
Saves preferences.

### `POST /api/users/behavior`
Records a behavioral event for the adaptive engine. Updates EMA-weighted cognitive load on the user's profile and returns a mode suggestion when load crosses a threshold.

Body:
```json
{
  "error_rate": 0.4,
  "slow_typing_rate": 0.3,
  "help_click_rate": 0.2,
  "page_dwell_seconds": 120.0
}
```

Response:
```json
{
  "load": 0.31,
  "suggestion": null,
  "current_mode": "intermediate"
}
```

`suggestion` is `"novice"`, `"expert"`, or `null` when no change is recommended.

---

## Indian tax filing v2

### `POST /api/v2/calc/preview`
**Stateless tax computation.** No DB reads or writes; returns a fresh `TaxBreakdown`.

Body:
```json
{
  "gross_income": 1200000,
  "deductions": {"80c": 100000, "80d": 20000},
  "regime": "old",
  "is_salary_income": true,
  "fy": "2024-25",
  "age": 62
}
```

`age` is optional (defaults to 30). Senior citizens (60–79) get a ₹3L basic exemption under the old regime; super-seniors (80+) get ₹5L.

Response:
```json
{
  "regime": "old",
  "fy": "2024-25",
  "gross_income": 1200000,
  "age_category": "senior",
  "deductions_applied": {"80c": 100000, "80d": 20000},
  "taxable_income": 1030000,
  "slab_tax": 86500,
  "rebate_87a": 0,
  "tax_after_rebate": 86500,
  "surcharge": 0,
  "cess": 3460,
  "total_tax": 89960
}
```

422 on invalid `regime` (must be `"old"` or `"new"`).

---

### `POST /api/v2/filing/start`
**Compute and persist a filing.** Requires `filer` or `helper` role. Inputs come from either a `Form16` row or a manual JSON payload. Persists an `ITR1Filing` record, renders the PDF, and (optionally) emits WebSocket progress events.

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
  "total_tax": 89960,
  "tax_due": 0,
  "refund_due": 10040
}
```

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
    "slabTax": 86500,
    "rebate87A": 0,
    "surcharge": 0,
    "cess": 3460,
    "totalTaxLiability": 89960
  },
  "taxesPaid": {"tdsTotal": 100000}
}
```

### `GET /api/v2/filing/{filing_id}/status`
Quick summary without PDF / JSON payload:
```json
{
  "filing_id": 1,
  "status": "computed",
  "regime": "old",
  "assessment_year": "2025-26",
  "total_tax": 89960,
  "tax_due": 0,
  "refund_due": 10040
}
```

---

## XAI (Explainable AI)

### `POST /api/v2/explain/`
Returns plain-language explanations for each component of the tax breakdown.

Body:
```json
{
  "gross_income": 1200000,
  "deductions": {"80c": 100000},
  "regime": "new",
  "age": 30
}
```

Response:
```json
{
  "breakdown": {
    "gross_income": 1200000,
    "taxable_income": 1025000,
    "slab_tax": 56250,
    "total_tax": 58500
  },
  "explanations": [
    {
      "line": "standard_deduction",
      "amount": 75000,
      "plain_text": "A flat ₹75,000 standard deduction applies under the new regime."
    },
    {
      "line": "slab_tax",
      "amount": 56250,
      "plain_text": "Slab tax computed on ₹10,25,000 taxable income under FY 2024-25 new regime rates."
    }
  ]
}
```

---

### `POST /api/v2/explain/whatif`
Recomputes the breakdown with a modified deduction and returns the tax delta.

Body:
```json
{
  "gross_income": 1200000,
  "deductions": {"80c": 100000},
  "regime": "old",
  "age": 30,
  "whatif_deductions": {"80c": 150000}
}
```

Response:
```json
{
  "baseline_tax": 126360,
  "whatif_tax": 110960,
  "delta": -15400,
  "plain_text": "Increasing 80C from ₹1,00,000 to ₹1,50,000 saves ₹15,400 in tax."
}
```

---

### `POST /api/v2/explain/regime-compare`
Side-by-side comparison of old and new regime for the same income and deductions.

Body:
```json
{
  "gross_income": 1200000,
  "deductions": {"80c": 150000, "80d": 25000},
  "age": 30
}
```

Response:
```json
{
  "old_regime": {"total_tax": 110960, "taxable_income": 925000},
  "new_regime": {"total_tax": 108160, "taxable_income": 1125000},
  "recommendation": "new",
  "saving": 2800,
  "plain_text": "New regime saves ₹2,800. The 80C/80D deductions (₹1.75L) are not enough to offset old-regime slab rates for this income level."
}
```

---

## LangGraph chat workflow

These endpoints drive the full `interviewer → researcher → calculator → auditor` graph. Requires `LLM_PROVIDER` + matching API key in `.env`.

Thread state is persisted to PostgreSQL via `AsyncPostgresSaver` and survives backend restarts.

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
  "tax_breakdown": {"total_tax": 89960, "...": "..."},
  "audit_status": "passed",
  "audit_errors": null,
  "current_agent": "auditor"
}
```

### `POST /api/v2/filing/chat/message`
Body: `{"thread_id", "message"}`
Continues the thread. State is restored from `AsyncPostgresSaver`.

---

## Documents (Form 16)

### `POST /api/documents/upload`
**Authentication required.** Multipart upload.

Behavior:
1. File saved under `backend/app/uploads/`
2. Tesseract OCR extracts raw text (mock fallback if Tesseract not installed)
3. Heuristic detection: is this a Form 16?
4. If yes: regex-based structured extraction → `Form16Data` Pydantic model
5. If `extraction_confidence ≥ 0.25`: writes a `form16` row; status `"extracted"`
6. Else: returns `extraction_status: "review_required"` with extracted fields for correction
7. If not Form 16: returns `extraction_status: "ocr_only"` with raw text preview

Response (extracted Form 16):
```json
{
  "filename": "form16-asha.pdf",
  "extraction_status": "extracted",
  "extraction_confidence": 0.83,
  "form16_id": 7,
  "extracted_fields": {
    "employer_name": "ACME INDIA TECHNOLOGIES PVT LTD",
    "employer_pan": "ACMEP1234L",
    "employee_pan": "ABCDE1234F",
    "assessment_year": "2025-26",
    "gross_salary": 1200000.0,
    "deductions_80c": 150000.0,
    "deductions_80d": 25000.0,
    "tds_deducted": 100000.0
  }
}
```

---

## WebSocket

### `/api/ws/{client_id}`
Bi-directional channel. The backend pushes:

- `{event: "connected", client_id}` — on accept
- `{event: "echo", message}` — for inbound text (echo placeholder)
- `{event: "agent_activity", agent, message}` — broadcast from LangGraph nodes
- `{event: "filing.starting", user_id, regime}`
- `{event: "filing.calculating"}`
- `{event: "filing.complete", filing_id, regime, total_tax, tax_due, refund_due, pdf_url, json_url}`

---

## Adaptive UI / SDUI

### `GET /api/sdui/dashboard/{user_id}`
Returns a structured-dynamic-UI schema for the adaptive frontend. Schema reflects the user's current `preferred_mode`.

---

## Error model

Validation errors (Pydantic) → `422`:
```json
{
  "detail": [{"type": "missing", "loc": ["body", "regime"], "msg": "Field required"}],
  "message": "Validation error - please check your input"
}
```

Role not allowed → `403`:
```json
{"detail": "Role 'read_only' not permitted for this action."}
```

Database errors → `500`. Generic exceptions → `500` with `detail: "Internal server error"`.

---

## Curl recipes

```bash
# New regime ₹6L — full Section 87A rebate
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":600000,"deductions":{},"regime":"new","is_salary_income":true}'

# Senior citizen — old regime with ₹3L exemption
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":600000,"deductions":{},"regime":"old","is_salary_income":true,"age":65}'

# Register + log in
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.in","password":"Aa123456","full_name":"Asha Verma"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=asha@example.in&password=Aa123456"
# -> {"access_token":"eyJ...", "token_type":"bearer"}

# XAI explanation
curl -X POST http://localhost:8000/api/v2/explain/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"gross_income":1200000,"deductions":{"80c":150000},"regime":"old","age":30}'

# What-if analysis
curl -X POST http://localhost:8000/api/v2/explain/whatif \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"gross_income":1200000,"deductions":{"80c":100000},"regime":"old","age":30,"whatif_deductions":{"80c":150000}}'

# Compute and persist a filing
curl -X POST http://localhost:8000/api/v2/filing/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id":1,"regime":"old","salary":{"gross":1200000,"tds":100000},"deductions":{"80c":100000}}'

# Download the PDF
curl http://localhost:8000/api/v2/filing/1/pdf \
  -H "Authorization: Bearer <token>" \
  -o itr1-1.pdf
```
