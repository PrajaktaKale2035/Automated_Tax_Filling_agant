# Setup and Testing Guide

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | any recent | Runs PostgreSQL with pgvector |
| Python | 3.10+ | Tested on 3.14; use a venv, never global pip |
| Node.js | 18+ | Frontend (Vite / Vue 3) |
| Tesseract OCR | 4+ | Optional — Form 16 upload path only |

---

## Step 1: Start the database

```bash
# Only postgres is required. pgAdmin is optional. neo4j is unused.
docker-compose up -d postgres

# Confirm it is ready
docker exec tax-agent-db pg_isready -U taxagent
# postgresql://localhost:5432 - accepting connections
```

> **Connection string:** `postgresql://taxagent:taxagent_secure_password_2024@localhost:5436/tax_filing_db`
> Port 5436 on the host maps to 5432 inside the container (see `docker-compose.yml`).

---

## Step 2: Backend setup

```bash
cd backend

# Create isolated virtual environment (never use global pip)
python -m venv venv

# Activate it
.\venv\Scripts\activate        # Windows PowerShell / cmd
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### Configure environment variables

Copy the sample and fill in at least one LLM key:

```bash
cp .env.dev .env    # or just create backend/.env manually
```

Minimal `.env`:

```env
# --- Database (matches docker-compose.yml) ---
DATABASE_URL=postgresql://taxagent:taxagent_secure_password_2024@localhost:5436/tax_filing_db

# --- LLM provider (pick ONE of the three blocks below) ---

# Option A: Google Gemini (free tier available)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-flash-lite-latest

# Option B: OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4

# Option C: Ollama (fully local, no API key needed)
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=mistral
# OLLAMA_BASE_URL=http://localhost:11434

# --- Security ---
SECRET_KEY=replace_this_with_a_random_secret
# Generate ENCRYPTION_KEY with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=replace_this_with_output_of_above_command
```

> **Note:** The chat endpoints (`/api/v2/filing/chat/*`) require a working LLM.
> The deterministic endpoints (`/api/v2/calc/preview`, `/api/v2/filing/start`) run
> with no LLM at all — the tax engine is pure Python math.

### First-time database initialisation

```bash
# Create schema (DESTRUCTIVE — drops and recreates all tables)
python -m scripts.recreate_db --force

# Ingest the curated FY 2024-25 ITR-1 rulebook into pgvector
python -m app.rag.ingest
# Expected: "Ingested 57 chunk(s) from 'tax_rules.txt' into 'itr_rulebook'."

# Verify what was ingested
python -m app.rag.ingest --list
```

### Start the backend

```bash
python -m uvicorn app.main:app --reload
```

API at `http://localhost:8000`. Swagger UI at `http://localhost:8000/api/docs`.

---

## Step 3: Frontend setup

```bash
# From the project root (not backend/)
npm install
npm run dev
```

Frontend at `http://localhost:5173`.

---

## Adding more knowledge to the RAG

The ingest CLI supports any text or PDF source:

```bash
# Show what is currently in the DB
python -m app.rag.ingest --list

# Re-ingest the default rulebook (replaces collection)
python -m app.rag.ingest

# Add a custom .txt file without wiping existing chunks
python -m app.rag.ingest --file my_cbdt_circular.txt --append

# Ingest a whole folder of .txt files
python -m app.rag.ingest --dir extra_rules/ --pattern "*.txt" --append

# Ingest a text-based PDF (install pypdf first; scanned PDFs need Tesseract OCR)
pip install pypdf
python -m app.rag.ingest --pdf income_tax_act_chapter4.pdf --append

# Use a separate collection (does not touch itr_rulebook)
python -m app.rag.ingest --file gst_rules.txt --collection gst_kb
```

> **Scanned vs text PDFs:** `--pdf` only works on PDFs with selectable text (digital PDFs).
> Scanned Form 16 images and similar documents must go through
> `POST /api/documents/upload` which runs Tesseract OCR automatically.

---

## Step 4: Smoke tests

### REST smoke tests

```bash
# Stateless tax preview (no LLM, no DB write)
curl -s -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":600000,"deductions":{},"regime":"new","is_salary_income":true}' | python -m json.tool
# Expected: total_tax = 0  (full Section 87A rebate at 6L income, new regime)

# LangGraph chat start (requires LLM provider configured in .env)
curl -s -X POST http://localhost:8000/api/v2/filing/chat/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"initial_message":"I earn 12 lakh per year"}' | python -m json.tool
# Expected: research_results array with 6 items, tax_breakdown populated, audit_status: "passed"

# RAG similarity search (no LLM needed)
curl -s "http://localhost:8000/api/v2/rag/search?q=standard+deduction&k=3" | python -m json.tool
# Expected: 3 results with section, content, score fields
```

### Automated test suite

```bash
cd backend
python -m pytest tests/ -q
# Expected: 75 passed, 0 warnings
```

---

## Architecture

```
START
  └─► interviewer_node   (LLM extracts structured fields; grounded by RAG context)
          │
          ▼
      research_and_calc  (runs researcher + calculator in parallel via asyncio.gather)
       │            │
       ▼            ▼
  researcher_node   calculator_node
  (pgvector RAG,    (deterministic tax_engine_in,
   6 chunks)         no LLM arithmetic)
          │
          ▼
      auditor_node   (5 property-based invariants; always ends the graph)
          │
         END
```

### LLM provider selection logic

| `LLM_PROVIDER` env | Keys present | Provider used |
|---|---|---|
| `ollama` | any | Ollama (local, no key) |
| `gemini` | any | Google Gemini |
| `openai` | any | OpenAI |
| _(unset)_ | OpenAI key | OpenAI |
| _(unset)_ | Gemini key only | Gemini |
| _(unset)_ | neither | Ollama (fallback) |

Change `LLM_PROVIDER` in `backend/.env` to switch providers without touching code.

---

## Troubleshooting

### "connection refused" on startup

```bash
# Check DB container is running
docker ps --filter name=tax-agent-db

# If exited, start it
docker start tax-agent-db

# Wait for readiness
docker exec tax-agent-db pg_isready -U taxagent
```

### LLM quota exhausted (Gemini 429)

Change `GEMINI_MODEL` in `backend/.env` to another available model:
- `gemini-flash-lite-latest`
- `gemini-2.5-flash-lite`
- `gemini-flash-latest`
- `gemini-pro-latest`

Or switch to `LLM_PROVIDER=ollama` for fully local operation.

### "No connection could be made" (Ollama)

```bash
# Start Ollama service, then pull the model
ollama serve
ollama pull mistral
```

### pgvector extension missing

```bash
docker exec -it tax-agent-db psql -U taxagent -d tax_filing_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### RAG sidebar empty / 0 results

```bash
# Check chunk count
docker exec -it tax-agent-db psql -U taxagent -d tax_filing_db \
  -c "SELECT COUNT(*) FROM rag_documents;"

# If 0 rows, re-run ingest
cd backend && python -m app.rag.ingest
```

---

## User data isolation

All endpoints that touch user-specific data (filings, Form 16 uploads) require JWT authentication. Key isolation rules:

- **Uploaded files** land in `backend/uploads/{user_id}/{uuid}.ext` — each user has their own subdirectory.
- **`GET /api/v2/filing/{id}/pdf|json|status`** and **`GET /api/v2/filings`** require a Bearer token and filter to `user_id = current_user.id`. A user cannot access another user's filings.
- **`GET /api/v2/rag/search`** is open (it queries shared rulebook data — no user data involved).
- The `rag_documents` table has no `user_id` — it stores shared ITR rulebook chunks, not user-uploaded content.

---

## What is NOT in this project

| Thing | Status |
|---|---|
| Rust tax engine (`tax_engine_rs`) | Removed — pure Python `tax_engine_in` used instead |
| Neo4j / GraphRAG | Not used — pgvector handles all RAG |
| `requirements-phase1.txt` | Removed — single `requirements.txt` |
| `scripts/ingest_neo4j.py` | File still exists (legacy) but is not called anywhere |
| AutoGen agents (`app/autogen_agents/`) | Removed — LangGraph only |
| US forms (W-2, 1099, Form 1040) | Removed — Indian ITR-1 only |
| AsyncPostgresSaver (LangGraph) | Deferred to Phase 3+ |
| E-filing submission to incometax.gov.in | Out of scope |
