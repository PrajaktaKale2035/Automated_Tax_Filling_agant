# How to Use the Indian Tax Filing AI Agent

A walkthrough for end-to-end usage: starting the app, signing up, computing a filing, downloading the ITR-1 JSON, exploring the rulebook, and using the chat assistant.

---

## 0. Before you start

### One-time setup
1. **Postgres + pgvector** is running. From repo root:
   ```bash
   docker-compose up -d postgres
   ```
2. **Backend Python deps** installed in a venv:
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```
3. **Backend `.env`** exists at `backend/.env`. If missing:
   ```bash
   cp .env.example .env
   # Generate a real Fernet encryption key:
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # paste the output as ENCRYPTION_KEY in .env
   ```
   For the LangGraph chat workflow, also set `OPENAI_API_KEY`. The deterministic endpoints (calc preview, filing start, RAG search) run without any LLM keys.
4. **Schema** is up to date and the rulebook is ingested:
   ```bash
   python -m scripts.recreate_db --force          # one-time, destroys data
   python -m app.rag.ingest                       # writes 7 chunks to rag_documents
   ```
5. **Frontend deps** installed:
   ```bash
   cd ..
   npm install
   ```

### Starting the app every day
Two terminals (or use `run_app.bat` on Windows):

```bash
# Terminal 1 - backend
cd backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload
# -> http://localhost:8000

# Terminal 2 - frontend
npm run dev
# -> http://localhost:8080
```

Health check: visit <http://localhost:8000/api/health> — you should see `{"status":"healthy","database":"healthy"}`.

---

## 1. Sign up & log in

1. Go to <http://localhost:8080/register>.
2. Enter Full Name, Email, Password.
   **Password rules**: minimum 8 characters, at least one uppercase letter, at least one digit (e.g. `Test1234`, `MyPass99`).
3. Click **Create account**. You're redirected to the login page.
4. Log in with the same email + password.

If signup fails the page now shows the exact reason ("Password must contain at least one uppercase letter", "Email already registered", etc.).

---

## 2. The data in the system: real vs. mock

The system holds **real data** in Postgres for everything that flows through the data pipeline. The mock data the prototype shipped with is being phased out.

| Page | Data source | Status |
|---|---|---|
| **Filings list** (`/filings`) | `GET /api/v2/filings` → `itr1_filings` table | ✅ Real |
| **Reports** (`/reports`) | hardcoded sample numbers in the .vue file | ⚠️ Mock (display only) |
| **Documents** (`/documents`) | `POST /api/documents/upload` → `form16` table | ✅ Real |
| **Settings**, **Help**, etc. | local Pinia state | n/a |
| **Chat assistant** | LangGraph backend (`/api/v2/filing/chat/*`) when wired; frontend LangChain.js otherwise | ⚠️ Depends on which UI you click |

To verify your filings table has real rows:
```bash
curl http://localhost:8000/api/v2/filings | python -m json.tool
```

To inspect the database directly:
```bash
docker exec -it tax-agent-db psql -U taxagent -d tax_filing_db
\dt                                  -- list tables
SELECT id, regime, total_tax, tax_due FROM itr1_filings;
SELECT id, employer_name, gross_salary FROM form16;
SELECT id, source, topic, LEFT(content, 60) FROM rag_documents;
\q
```

---

## 3. Compute a tax preview (no login required)

The simplest way to see the engine working:

### From the API directly
```bash
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{
    "gross_income": 1200000,
    "deductions": {"80c": 100000, "80d": 20000},
    "regime": "old",
    "is_salary_income": true
  }'
```

You get a full `TaxBreakdown`:
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

### From the frontend
The frontend's tax tools (`src/agents/tools/taxCalculationTools.ts`) call this endpoint internally — `compare_regimes`, `calculate_income_tax`, etc. all hit the same engine.

---

## 4. Create a real filing

### Option A — manual entry (any user, no Form 16)

```bash
# Replace user_id with one from POST /api/auth/register
curl -X POST http://localhost:8000/api/v2/filing/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "regime": "new",
    "salary": {"gross": 1500000, "tds": 50000},
    "deductions": {}
  }'
```

Response includes a `filing_id`:
```json
{"filing_id": 2, "status": "computed", "regime": "new", "total_tax": ..., ...}
```

### Option B — from a Form 16 upload

1. Go to <http://localhost:8080/documents> and upload a Form 16 PDF/image.
2. The OCR + extractor populates a row in `form16` and returns a `form16_id`.
3. Start filing:
   ```bash
   curl -X POST http://localhost:8000/api/v2/filing/start \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1, "regime": "old", "form16_id": 7}'
   ```

### Where it goes

After `/start` succeeds:
- A new row in `itr1_filings` (real data, queryable in psql)
- A PDF rendered to `backend/app/uploads/itr1/{id}.pdf`
- ITR-1 JSON in IT Department schema persisted in `itr1_filings.itr1_json`

Visit <http://localhost:8080/filings> in the browser — your filing now appears in the list (real data, not mock).

---

## 5. Download the ITR-1 (E-File button)

On the **Filings** page, three buttons per filing:

- **Download PDF** — `GET /api/v2/filing/{id}/pdf`
- **Export ITR-1 JSON** — `GET /api/v2/filing/{id}/json`
- **E-File (Stub)** — downloads the same JSON, then shows a dialog explaining how to upload it manually at <https://incometax.gov.in> via *e-File → File Income Tax Return → Upload Pre-filled JSON*. Real e-filing submission is on the roadmap.

Direct curl:
```bash
curl http://localhost:8000/api/v2/filing/1/pdf  -o itr1.pdf
curl http://localhost:8000/api/v2/filing/1/json | python -m json.tool
```

---

## 6. Inspecting the ITR rulebook (RAG)

The system ships with a curated FY 2024-25 rulebook (`backend/tax_rules.txt`) ingested into pgvector as 7 chunks. You can query it three ways:

### Via the new REST endpoint
```bash
curl "http://localhost:8000/api/v2/rag/search?q=surcharge%20for%201%20crore&k=3" | python -m json.tool
```

Returns:
```json
{
  "query": "surcharge for 1 crore",
  "k": 3,
  "topic_filter": null,
  "results": [
    {
      "content": "6. Surcharge:\n   - 10% for income above ₹50 Lakhs\n   - 15% for income above ₹1 Crore...",
      "source": "tax_rules.txt",
      "topic": "slabs",
      "score": 0.78
    },
    ...
  ]
}
```

### Via the Python CLI
```bash
cd backend
.\venv\Scripts\activate
python -m app.rag.retriever
```

### Via direct SQL
```bash
docker exec -it tax-agent-db psql -U taxagent -d tax_filing_db
SELECT chunk_index, topic, LEFT(content, 80) FROM rag_documents ORDER BY chunk_index;
```

### Topic filter

The ingester auto-tags each chunk with one of: `slabs`, `80C`, `80D`, `rebate-87a`, `surcharge`, `cess`, `tds`, `standard-deduction`, `form-16`, `identity`. Use `&topic=80C` to narrow:
```bash
curl "http://localhost:8000/api/v2/rag/search?q=deduction&topic=80C"
```

### How to expand the rulebook
Drop additional `.txt` or PDF-extracted-text files in a folder, then:
```bash
python -c "from app.rag.ingest import ingest_directory; print(ingest_directory('path/to/folder'))"
```
The official Income Tax Act 1961, ITR-1 instructions, Finance Act 2024, and CBDT circulars are good candidates for a future ingest.

---

## 7. The chat assistant

There are two chat surfaces in the project:

### A. Frontend LangChain.js chat (`/chat` page)
Runs in the browser. Configured via `src/agents/llm/LLMProvider.ts`. Supports OpenAI, Anthropic, Gemini, etc. Requires the corresponding API key in the **frontend** `.env` (Vite env vars must be prefixed `VITE_`):
```bash
# In project root
echo "VITE_OPENAI_API_KEY=sk-..." > .env.local
echo "VITE_GEMINI_API_KEY=AIza..." >> .env.local
npm run dev
```
This chat does not currently call the pgvector RAG — it answers from the LLM's general knowledge plus its frontend tool set.

### B. Backend LangGraph chat (`/api/v2/filing/chat/*`)
Runs the full agent workflow on the backend: interviewer → researcher (real RAG) → calculator (real engine) → auditor. Currently exposed only via REST; no UI page is wired to it yet.

```bash
# Start a chat thread (requires OPENAI_API_KEY in backend/.env)
curl -X POST http://localhost:8000/api/v2/filing/chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "initial_message": "I earn 12 lakh salary, paid 1L into PPF and 25k for health insurance. Old or new regime?"
  }'
```

The response includes:
- `messages` — the conversation
- `user_profile` — extracted fields (income, regime, deductions)
- `research_results` — top RAG chunks the researcher pulled
- `tax_breakdown` — the deterministic engine's output
- `audit_status` — invariant check result
- `thread_id` — pass to `/chat/message` to continue

To continue:
```bash
curl -X POST http://localhost:8000/api/v2/filing/chat/message \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "tax-1-a1b2c3d4", "message": "What if I bumped 80C to 1.5L?"}'
```

> **Note**: backend chat sessions live in memory only (`InMemorySaver`). They don't survive a server restart. Switching to `AsyncPostgresSaver` is on the roadmap.

---

## 8. Testing the system

### Backend test suite
```bash
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -q
```

Expected: `75 passed`. Includes:
- 33 tax engine tests
- 8 Form 16 extractor tests
- 4 live pgvector RAG integration tests (skipped if Postgres is down)
- 11 filing API tests (preview, manual + form16_id, downloads, 404 paths)
- 3 WebSocket completion-event tests
- 6 LangGraph integration tests
- 5 hypothesis metamorphic tests
- 5 supporting tests

### Manual smoke test recipe
```bash
# 1. Health
curl http://localhost:8000/api/health

# 2. Tax preview (no login)
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":600000,"deductions":{},"regime":"new","is_salary_income":true}'
# total_tax must be 0 (Section 87A full rebate)

# 3. RAG retrieval
curl "http://localhost:8000/api/v2/rag/search?q=80C&k=1"

# 4. List filings
curl http://localhost:8000/api/v2/filings

# 5. Visit the docs
open http://localhost:8000/api/docs
```

---

## 9. Common tasks cheat sheet

| Task | Command |
|---|---|
| Reset the database | `cd backend && python -m scripts.recreate_db --force` |
| Re-ingest the rulebook | `cd backend && python -m app.rag.ingest` |
| Run all tests | `cd backend && python -m pytest -q` |
| Restart backend | Ctrl+C in terminal, then `python -m uvicorn app.main:app --reload` |
| Restart frontend | Ctrl+C, then `npm run dev` |
| View Postgres directly | `docker exec -it tax-agent-db psql -U taxagent -d tax_filing_db` |
| Generate a Fernet key | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| See routes | <http://localhost:8000/api/docs> |

---

## 10. Troubleshooting

### "Sign up not working" / 500 Internal server error
**Cause**: weak password (no uppercase / no digit) or password < 8 chars.
**Fix**: backend now returns clean 422 with the rule that failed; the Register page also shows the rules. Use `Test1234` or similar.

### "E-File Now" button does nothing / shows error
**Cause**: previous version called `/api/filing/submit` which was deleted in Phase 0.
**Fix**: now calls `GET /api/v2/filing/{id}/json` and downloads the file. Real submission to incometax.gov.in is not yet implemented.

### Filings list shows wrong data / mock
**Cause**: previous version had hardcoded mock filings.
**Fix**: now calls `GET /api/v2/filings`. If you see no filings at all, create one via `/filing/new` or the `/api/v2/filing/start` curl above.

### Chat says "graph execution failed: Error code: 401"
**Cause**: `OPENAI_API_KEY` missing or wrong in `backend/.env`.
**Fix**: paste a real key into `backend/.env`, restart uvicorn.

### `Tesseract not installed`
**Cause**: Tesseract OCR binary isn't on PATH.
**Fix**: install Tesseract from <https://github.com/UB-Mannheim/tesseract/wiki>, add to PATH. Or skip — the OCR layer falls back to a mock string when missing, which still lets the rest of the pipeline run.

### Postgres is not reachable
```bash
docker-compose ps                  # check status
docker-compose logs postgres       # see errors
docker-compose up -d postgres      # restart
```

### `psycopg2-binary` build error on Python 3.13/3.14
The pinned `2.9.9` lacks wheels for new Python. The current `requirements.txt` uses `>=2.9.9` so newer versions are picked. If you still hit this, `pip install psycopg2-binary --upgrade`.

---

## 11. What's not built yet

These are tracked as future work, not bugs:

- **Real e-filing submission** to incometax.gov.in — currently a download-and-upload stub
- **Real IT Department PDF ingestion** for RAG (Income Tax Act 1961, ITR-1 instructions, Finance Act 2024, CBDT circulars) — currently using the curated `tax_rules.txt`
- **AsyncPostgresSaver** for LangGraph checkpointing — currently `InMemorySaver`
- **Frontend chat → backend LangGraph** wiring — `Chat.vue` runs frontend agents, `/chat/start` runs backend agents, no UI bridges them yet
- **Reports page** still uses sample numbers
- **Admin RBAC** — `/api/users/...` admin checks are TODOs

See `docs/MIGRATION_NOTES.md` for the full changelog of what was migrated.

---

## 12. Where things live (quick map)

| What | Where |
|---|---|
| Tax math (single source of truth) | `backend/app/services/tax_engine_in.py` |
| ITR-1 JSON output | `backend/app/services/itr1_json_builder.py` |
| ITR-1 PDF output | `backend/app/services/pdf_generator.py` |
| Form 16 extractor | `backend/app/services/form16_extractor.py` |
| Backend RAG ingest | `backend/app/rag/ingest.py` |
| Backend RAG retriever | `backend/app/rag/retriever.py` |
| Curated rulebook | `backend/tax_rules.txt` |
| LangGraph workflow | `backend/app/agents_v2/{graph,nodes,state}.py` |
| REST endpoints | `backend/app/api/filing_v2.py`, `documents.py`, `auth.py`, `users.py`, `ws.py` |
| Frontend tax client | `src/agents/tools/taxCalculationTools.ts` |
| Frontend filings page | `src/pages/Filings.vue` |
| Frontend register/login | `src/pages/{Register,Login}.vue` + `src/stores/authStore.ts` |
| Backend env | `backend/.env` (gitignored) — copy from `.env.example` |
| Frontend env | `.env.local` at repo root (Vite convention; gitignored) |
