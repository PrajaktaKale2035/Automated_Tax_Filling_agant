# System Walkthrough — Indian ITR-1 AI Filing Agent

## What the system does

A conversational, multi-agent system for Indian ITR-1 income tax filing (FY 2024-25 / AY 2025-26). Users can:

1. **Chat** with the agent to compute their tax and get rulebook-grounded answers.
2. **Submit** directly via a structured API call (manual entry or uploaded Form 16).
3. **Explore** their tax breakdown through the XAI panel — plain-language explanations, what-if analysis, and regime comparison.
4. **Get guided** by the adaptive engine, which adjusts the UI mode based on measured interaction patterns.

---

## Multi-agent workflow (LangGraph)

Every chat message triggers a full graph run:

```
interviewer → research_and_calc → auditor → END
```

Thread state is persisted to PostgreSQL via `AsyncPostgresSaver` and survives backend restarts.

### 1. Interviewer node

- Builds a system prompt from `_INTERVIEWER_SYSTEM_PROMPT` and any RAG context injected from the previous turn.
- Calls the configured LLM (Gemini / OpenAI / Ollama) with `await asyncio.wait_for(llm.ainvoke(...), timeout=30)`.
- Parses the `EXTRACTION: {...}` JSON tag from the LLM reply.
- Updates `user_profile` in the graph state with extracted fields (`income_salary`, `regime`, `deductions_80c/80d`, `age`, `pan`, ...).
- On LLM errors (quota 429, 503, timeout) returns a graceful message and lets the graph continue.

### 2. Researcher node (parallel)

- Runs simultaneously with the calculator via `asyncio.gather`.
- Queries the `rag_documents` pgvector table using cosine similarity.
- Embeds the query with `SentenceTransformer all-MiniLM-L6-v2` (384-dim, fully local, no API cost).
- Returns up to 6 rulebook chunks (section, description, score).
- The next interviewer turn injects these chunks into the system prompt so answers cite specific amounts.

### 3. Calculator node (parallel)

- Calls `tax_engine_in.compute_filing()` — pure Python, no LLM arithmetic.
- FY 2024-25 rules: slabs, standard deduction (₹75K new / ₹50K old), 80C/80D caps, rebate u/s 87A, surcharge bands, 4% Health & Education Cess.
- Age-aware: senior citizens (60+) get ₹3L basic exemption; super-seniors (80+) get ₹5L under old regime.
- Returns a `TaxBreakdown` with `gross_income`, `taxable_income`, `slab_tax`, `rebate_87a`, `tax_after_rebate`, `surcharge`, `cess`, `total_tax`, `age_category`.

### 4. Auditor node

Validates 25 metamorphic invariants on the `TaxBreakdown`:

- Taxable income ≤ gross income
- All components are non-negative
- `total_tax = tax_after_rebate + surcharge + cess` (±₹1 rounding tolerance)
- Rebate ≤ slab_tax; effective rate < 40%
- Cess = exactly 4% of (tax + surcharge)
- Senior exemption ≥ general citizen exemption
- Monotonicity: higher income → higher or equal tax
- No surcharge below ₹50L; surcharge present above ₹50L
- And more — see `tests/test_metamorphic.py`

Returns `audit_status: "passed"` or `"failed"`. The graph always ends here (no retry loop, since the calculator is deterministic).

---

## XAI (Explainable AI)

Three stateless endpoints powered by `services/xai_engine.py`:

- **`POST /api/v2/explain/`** — every component of the tax breakdown gets a plain-language sentence (e.g. "A flat ₹75,000 standard deduction applies under the new regime.")
- **`POST /api/v2/explain/whatif`** — change a deduction value and see the tax delta (e.g. "Increasing 80C from ₹1L to ₹1.5L saves ₹15,400.")
- **`POST /api/v2/explain/regime-compare`** — side-by-side old vs new with the lower-tax option highlighted and a plain-language reason.

The Reports page surfaces all three in a collapsible XAI panel: click any filing row → line-item accordion with tabs for Breakdown and Compare Regimes.

---

## Adaptive engine

`POST /api/users/behavior` receives three real-time signals after each user interaction:

| Signal | Weight |
|---|---|
| Error rate (form validation errors per action) | 40% |
| Slow typing rate (keystrokes below threshold wpm) | 30% |
| Help click rate (help/tooltip clicks per action) | 30% |

The engine computes an EMA-weighted cognitive load score. When load crosses a threshold:
- `load < 0.20` → suggest `expert` mode
- `load > 0.50` → suggest `novice` mode
- Otherwise → no suggestion (`null`)

The suggestion is returned in the API response and can be shown as a non-intrusive prompt in the UI.

---

## Direct filing path (no chat)

`POST /api/v2/filing/start` accepts either:
- A manual `salary` + `deductions` JSON payload, **or**
- A `form16_id` referencing a previously uploaded and OCR-extracted Form 16.

Requires the user's `role` to be `filer` or `helper` (enforced by `require_role()` in `api/deps.py`).

It runs the tax engine, builds the IT Dept ITR-1 JSON, renders the PDF, persists an `itr1_filings` row, and optionally pushes WebSocket events to the `client_id` channel.

---

## Form 16 upload

`POST /api/documents/upload` accepts a PDF or image of a Form 16 certificate.

- Tesseract OCR extracts the raw text.
- `form16_extractor.py` parses employer PAN, gross salary, TDS deducted, 80C/80D deductions.
- If extraction confidence ≥ 0.25, stores a `form16` row and returns `form16_id`; otherwise returns `extraction_status: "review_required"`.
- The frontend stores the extracted data in `agentStore.form16Data` and pre-fills the NewFiling page.

---

## Outputs

- **ITR-1 JSON** — IT Department schema shape; accessible at `GET /api/v2/filing/{id}/json`.
- **ITR-1 PDF** — rendered with ReportLab in INR Indian grouping; accessible at `GET /api/v2/filing/{id}/pdf`.
- **WebSocket events** — `filing.starting`, `filing.calculating`, `filing.complete` pushed to the `client_id` channel in real time.
- **XAI explanations** — on-demand via `/api/v2/explain/*`; shown inline in Reports.

---

## Full end-to-end test

```bash
# 1. Register and log in
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.in","password":"Aa123456","full_name":"Asha Verma"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=asha@example.in&password=Aa123456" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Tax preview (senior citizen, old regime)
curl -s -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"gross_income":800000,"deductions":{"80c":150000},"regime":"old","is_salary_income":true,"age":65}' \
  | python -m json.tool

# 3. XAI explanation
curl -s -X POST http://localhost:8000/api/v2/explain/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"gross_income":800000,"deductions":{"80c":150000},"regime":"old","age":65}' \
  | python -m json.tool

# 4. Regime comparison
curl -s -X POST http://localhost:8000/api/v2/explain/regime-compare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"gross_income":800000,"deductions":{"80c":150000},"age":65}' \
  | python -m json.tool

# 5. Start a chat session (requires LLM key in .env)
curl -s -X POST http://localhost:8000/api/v2/filing/chat/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id":1,"initial_message":"I earn 8 lakh, I am 65 years old, old regime"}' \
  | python -m json.tool
# Expect: thread_id, research_results, tax_breakdown, audit_status: "passed"

# 6. Continue the conversation
curl -s -X POST http://localhost:8000/api/v2/filing/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"thread_id":"tax-1-XXXXX","message":"I also have 80C investments of 1.5 lakh"}' \
  | python -m json.tool

# 7. One-shot filing
curl -s -X POST http://localhost:8000/api/v2/filing/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id":1,"regime":"old","salary":{"gross":800000,"tds":30000},"deductions":{"80c":150000}}' \
  | python -m json.tool

# 8. Download the PDF
curl -o itr1.pdf http://localhost:8000/api/v2/filing/1/pdf \
  -H "Authorization: Bearer $TOKEN"
```

---

## Frontend pages

| Route | Component | Purpose |
|---|---|---|
| `/` | `LandingPage.vue` | Public landing — AI feature showcase (XAI, adaptive engine, senior slabs) |
| `/register` | `Register.vue` | User registration |
| `/login` | `Login.vue` | JWT login |
| `/dashboard` | `Index.vue` | Dashboard |
| `/chat` | `Chat.vue` | Conversational agent; RAG sidebar shows rulebook sources |
| `/filings` | `Filings.vue` | List past ITR-1 filings; download PDF / JSON |
| `/filing/new` | `NewFiling.vue` | Manual entry form (pre-filled from Form 16 if uploaded) |
| `/filing/wizard` | `WizardFiling.vue` | Structured step-by-step filing with behavioral tracking |
| `/filing/grid` | `FilingGrid.vue` | Expert direct-grid entry |
| `/reports` | `Reports.vue` | Tax summary + XAI explanation panel (line items, what-if, regime compare) |
| `/documents` | `Documents.vue` | Form 16 upload + OCR extraction |
| `/settings` | `Settings.vue` | Profile and preferences (regime, mode, theme) |
