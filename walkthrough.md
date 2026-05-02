# System Walkthrough — Indian ITR-1 AI Filing Agent

## What the system does

This is a conversational, multi-agent system for Indian ITR-1 income tax filing (FY 2024-25 / AY 2025-26). Users can either:

1. **Chat** with the agent to compute their tax and get rulebook-grounded answers.
2. **Submit** directly via a structured API call (manual entry or uploaded Form 16).

---

## Multi-agent workflow (LangGraph)

Every chat message triggers a full graph run:

```
interviewer → research_and_calc → auditor → END
```

### 1. Interviewer node

- Builds a system prompt from `_INTERVIEWER_SYSTEM_PROMPT` and any RAG context injected from the previous turn.
- Calls the configured LLM (Gemini / OpenAI / Ollama) with `await asyncio.wait_for(llm.ainvoke(...), timeout=30)`.
- Parses the `EXTRACTION: {...}` JSON tag from the LLM reply.
- Updates `user_profile` in the graph state with extracted fields (`income_salary`, `regime`, `deductions_80c/80d`, `age`, `pan`, ...).
- On LLM errors (quota 429, 503, timeout) returns a graceful message and lets the graph continue — the researcher still runs and populates the RAG sidebar.

### 2. Researcher node (parallel)

- Runs simultaneously with the calculator via `asyncio.gather`.
- Queries the `rag_documents` pgvector table using cosine similarity.
- Embeds the query with `SentenceTransformer all-MiniLM-L6-v2` (384-dim, fully local, no API cost).
- Returns up to 6 rulebook chunks (section, description, score).
- The next interviewer turn injects these chunks into the system prompt so answers cite specific amounts.

### 3. Calculator node (parallel)

- Calls `tax_engine_in.compute_filing()` — pure Python, no LLM arithmetic.
- FY 2024-25 rules: slabs, standard deduction (₹75K new / ₹50K old), 80C/80D caps, rebate u/s 87A, surcharge bands, 4% Health & Education Cess.
- Returns a `TaxBreakdown` dict with `gross_income`, `taxable_income`, `slab_tax`, `rebate_87a`, `tax_after_rebate`, `surcharge`, `cess`, `total_tax`.

### 4. Auditor node

Validates 5 property-based invariants on the `TaxBreakdown`:

1. Taxable income ≤ gross income
2. All components are non-negative
3. `total_tax = tax_after_rebate + surcharge + cess` (±₹1 rounding tolerance)
4. Rebate ≤ slab_tax
5. Effective rate < 50%

Returns `audit_status: "passed"` or `"failed"`. Errors are included in the API response for the frontend to display — the graph always ends here (no retry loop, since the calculator is deterministic).

---

## Direct filing path (no chat)

`POST /api/v2/filing/start` accepts either:
- A manual `salary` + `deductions` JSON payload, **or**
- A `form16_id` referencing a previously uploaded and OCR-extracted Form 16.

It runs the tax engine, builds the IT Dept ITR-1 JSON, renders the PDF, persists an `itr1_filings` row, and optionally pushes WebSocket events to the `client_id` channel.

---

## Form 16 upload

`POST /api/documents/upload` accepts a PDF or image of a Form 16 certificate.

- Tesseract OCR extracts the raw text.
- `form16_extractor.py` parses employer PAN, gross salary, TDS deducted, 80C/80D deductions.
- If extraction confidence ≥ 0.25, stores a `form16` row and returns `form16_id`; otherwise returns `extraction_status: "review_required"`.

---

## Outputs

- **ITR-1 JSON** — IT Department schema shape; accessible at `GET /api/v2/filing/{id}/json`.
- **ITR-1 PDF** — rendered with ReportLab in INR Indian grouping; accessible at `GET /api/v2/filing/{id}/pdf`.
- **WebSocket events** — `filing.starting`, `filing.calculating`, `filing.complete` pushed to the `client_id` channel in real time.

---

## Full end-to-end test

```bash
# 1. Start a chat session
curl -s -X POST http://localhost:8000/api/v2/filing/chat/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"initial_message":"I earn 12 lakh, new regime"}' | python -m json.tool
# Expect: thread_id, 6 research_results, tax_breakdown, audit_status: "passed"

# 2. Continue the conversation (replace thread_id)
curl -s -X POST http://localhost:8000/api/v2/filing/chat/message \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"tax-1-XXXXX","message":"I also have 80C investments of 1.5 lakh"}' | python -m json.tool
# Expect: updated user_profile with deductions_80c, recalculated tax_breakdown

# 3. One-shot filing (no chat)
curl -s -X POST http://localhost:8000/api/v2/filing/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"regime":"new","salary":{"gross":1200000,"tds":50000},"deductions":{"80c":150000}}' \
  | python -m json.tool
# Expect: filing_id, total_tax, tax_due/refund_due

# 4. Download the PDF
curl -o itr1.pdf http://localhost:8000/api/v2/filing/1/pdf
```

---

## Frontend pages

| Route | Component | Purpose |
|---|---|---|
| `/chat` | `Chat.vue` | Conversational agent; RAG sidebar shows rulebook sources |
| `/filings` | `Filings.vue` | List past ITR-1 filings; download PDF / JSON |
| `/wizard` | `WizardFiling.vue` | Structured step-by-step filing form |
| `/reports` | `Reports.vue` | Tax summary visualisations |
| `/documents` | `Documents.vue` | Form 16 upload |
