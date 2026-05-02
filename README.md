# Indian Tax Filing AI Agent — Automated ITR-1 Assistant

An intelligent, autonomous AI agent system for **Indian income tax filing (ITR-1 Sahaj)** built with **Vue 3**, **FastAPI**, **PostgreSQL + pgvector**, and **LangGraph multi-agent orchestration**.

> **Status**: Phase 0–4 complete. **Tax Year**: FY 2024-25 / AY 2025-26. **Form**: ITR-1 (salary + interest income).

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Documentation](#documentation)
- [Migration Notes (US → India)](#migration-notes-us--india)

---

## Overview

This project is an autonomous Indian tax filing system. It:

- 📄 **Extracts data from Form 16** (Indian salary TDS certificate) via Tesseract OCR + a Pydantic-backed extractor
- 🧮 **Calculates ITR-1 tax** through a deterministic engine in `backend/app/services/tax_engine_in.py` (no LLM math) — slabs, standard deduction, 80C, 80D, rebate u/s 87A, surcharge bands, 4% Health & Education Cess
- ✅ **Validates the filing** with metamorphic invariants (totals consistency, non-negativity, regime rules)
- 💡 **Compares old vs new regime** and recommends the lower-tax option
- 📝 **Produces ITR-1 outputs** — IT Department-shaped JSON and a rendered PDF in ITR-1 layout
- 🔎 **Grounds advice in the rulebook** via pgvector RAG over the Income Tax Act / ITR-1 instructions
- 🤖 **Runs a chat-driven workflow** through LangGraph: interviewer → researcher → calculator → auditor

---

## Features

### Multi-agent system (LangGraph only — AutoGen retired)

- **Interviewer** — extracts structured fields (`income_salary`, `regime`, `deductions_80c/80d`, `pan`, ...) from natural-language conversation via `EXTRACTION:` JSON
- **Researcher** — runs cosine-similarity RAG over the `rag_documents` pgvector table using `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Calculator** — invokes the deterministic `tax_engine_in` (never asks the LLM to do arithmetic)
- **Auditor** — validates the resulting `TaxBreakdown` against five property-based invariants

### Deterministic Indian tax engine (`tax_engine_in`)

- New regime slabs (FY 2024-25): 0/5/10/15/20/30 across ₹3L–₹15L+
- Old regime slabs: 0/5/20/30 across ₹2.5L–₹10L+
- Standard deduction: ₹75,000 (new) / ₹50,000 (old)
- Section 80C cap ₹1.5L, 80D cap ₹25,000 (old regime only)
- Rebate u/s 87A: ₹25,000 if income ≤ ₹7L (new) / ₹12,500 if income ≤ ₹5L (old)
- Surcharge bands: 10/15/25/37% (new regime caps at 25%)
- 4% Health & Education Cess on (tax + surcharge)

### Data pipeline

- **Document upload** → Tesseract OCR → Form 16 detection → Pydantic structured extraction → `form16` row
- **Filing path** (manual or Form 16) → tax engine → `itr1_filings` row → ITR-1 JSON + PDF
- **WebSocket events** — clients receive `filing.starting → filing.calculating → filing.complete` keyed to `client_id`

### Storage

- **PostgreSQL 16 + pgvector extension** for both relational data and embeddings
- 7 tables: `users`, `user_profiles`, `form16`, `itr1_filings`, `compliance_checks`, `audit_logs`, `rag_documents`

### Security

- JWT authentication, bcrypt password hashing
- Encrypted PAN and Aadhaar fields on `User` (via `app.security`)
- RBAC scaffolding (TODO admin checks in user routes)

### Adaptive UI (Vue 3)

- Three modes (novice / intermediate / expert) tracked via `UserProfile.preferred_mode`
- Frontend `taxCalculationTools.ts` calls the backend `/api/v2/calc/preview` so the same engine drives live preview, the LangGraph calculator, and the PDF

---

## Tech Stack

### Frontend
- Vue 3 (Composition API) + TypeScript
- Vite, Pinia, Vue Router
- TailwindCSS, Radix Vue, Lucide Vue
- LangChain.js for agent tooling (calls backend for tax math)

### Backend
- Python 3.10+ (tested on 3.14), FastAPI
- SQLAlchemy 2.0, Pydantic v2
- PostgreSQL 16 (`pgvector/pgvector:pg16` Docker image)
- LangGraph + LangChain (multi-provider: OpenAI / Gemini / Ollama)
- ReportLab (ITR-1 PDF rendering)
- pytest + hypothesis (75 tests, 0 warnings)

### AI / Data
- **LangGraph** — sole agent orchestration (AutoGen retired in Phase 0)
- **Multi-provider LLM** — Google Gemini, OpenAI GPT-4, or local Ollama; selected via `LLM_PROVIDER` in `.env`
- **SentenceTransformer all-MiniLM-L6-v2** — local embedding model (no API cost)
- **pgvector** — vector similarity search (replaces ChromaDB)

### Infrastructure
- Docker Compose (Postgres + optional Neo4j and pgAdmin)
- WebSockets for realtime filing events

---

## Quick Start

### Prerequisites
- Docker (for Postgres) — or a local Postgres 16+ with the `vector` extension
- Python 3.10+
- Node.js 18+
- Tesseract OCR (for Form 16 upload — optional in dev; the extractor falls back to a mock)

### 1. Start Postgres (with pgvector)

```bash
docker-compose up -d postgres
```

The compose file uses the `pgvector/pgvector:pg16` image, so the `vector` extension is available out of the box.

### 2. Backend setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

# Create the schema (DESTRUCTIVE - drops & recreates from models)
python -m scripts.recreate_db --force

# Ingest the curated Indian rulebook into pgvector
python -m app.rag.ingest

# Run the API
python -m uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`. Docs at `http://localhost:8000/api/docs`. OpenAPI schema at `/api/openapi.json`.

> **LLM key**: copy `backend/.env.dev` to `backend/.env` and set `LLM_PROVIDER` + the matching API key (Gemini, OpenAI, or Ollama) if you want the LangGraph chat flow (`/api/v2/filing/chat/start`). The deterministic endpoints (`/api/v2/calc/preview`, `/api/v2/filing/start`) work without any LLM. See `PHASE1_SETUP.md` for all provider options.

### 3. Frontend setup

```bash
npm install
npm run dev
```

Frontend at `http://localhost:5173`.

### 4. Smoke test

```bash
# Indian new-regime preview
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income": 600000, "deductions": {}, "regime": "new", "is_salary_income": true}'
# -> total_tax: 0 (full Section 87A rebate)
```

---

## Project Structure

```
Automated_Tax_Filling_agant/
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI app + lifespan + CORS
│   │   ├── database.py                   # SQLAlchemy engine, get_db, Base
│   │   ├── models.py                     # 7 tables (Indian schema)
│   │   ├── schemas.py                    # Pydantic request/response models
│   │   ├── crud.py                       # User / UserProfile / AuditLog CRUD
│   │   ├── security.py                   # JWT + bcrypt + AES encryption
│   │   ├── api/
│   │   │   ├── auth.py                   # /api/auth/login, /register, ...
│   │   │   ├── users.py                  # /api/users/...
│   │   │   ├── documents.py              # /api/documents/upload (OCR + Form 16)
│   │   │   ├── filing_v2.py              # /api/v2/calc/* and /api/v2/filing/*
│   │   │   ├── ws.py                     # /api/ws/{client_id} for realtime events
│   │   │   └── sdui.py                   # adaptive-UI dashboard
│   │   ├── agents_v2/                    # LangGraph workflow
│   │   │   ├── graph.py                  # StateGraph + InMemorySaver
│   │   │   ├── nodes.py                  # interviewer / researcher / calculator / auditor
│   │   │   └── state.py                  # TaxFilingState TypedDict
│   │   ├── rag/                          # pgvector RAG
│   │   │   ├── ingest.py                 # SentenceTransformer + DB writes
│   │   │   └── retriever.py              # cosine-distance similarity search
│   │   ├── services/
│   │   │   ├── tax_engine_in.py          # deterministic Indian tax engine
│   │   │   ├── tax_engine_in_constants.py # FY 2024-25 slabs / limits
│   │   │   ├── itr1_json_builder.py      # IT Dept ITR-1 JSON shape
│   │   │   ├── pdf_generator.py          # ITR-1 PDF (ReportLab)
│   │   │   ├── form16_extractor.py       # OCR text -> Form16Data
│   │   │   └── ocr.py                    # Tesseract wrapper
│   │   ├── websockets/manager.py         # per-client_id WS routing
│   │   └── sdui/                         # adaptive-UI schema
│   ├── scripts/
│   │   └── recreate_db.py                # CREATE EXTENSION vector + drop_all + create_all
│   ├── tests/                            # 75 tests, 0 warnings
│   │   ├── api/ rag/ services/ integration/
│   │   └── conftest.py                   # SQLite in-memory + StaticPool fixture
│   ├── tax_rules.txt                     # Curated FY 2024-25 rulebook (Phase 1 RAG corpus)
│   └── requirements.txt
├── src/                                  # Vue 3 frontend
│   ├── agents/tools/taxCalculationTools.ts # API client for /api/v2/calc/preview
│   ├── pages/ Filings/ WizardFiling/ Reports/ ...
│   └── components-vue/...
├── docs/
│   ├── setup/                            # database setup
│   ├── api/                              # API reference
│   ├── guides/                           # LangChain / providers
│   ├── superpowers/                      # design specs, audit, plans
│   └── MIGRATION_NOTES.md                # US -> India migration changelog
├── docker-compose.yml                    # postgres (pgvector), pgadmin, neo4j (optional)
└── package.json
```

---

## API Endpoints

### Health / metadata
- `GET /` — service metadata
- `GET /api/health` — Postgres connection check
- `GET /api/docs` — Swagger UI (schema at `/api/openapi.json`)

### Authentication
- `POST /api/auth/register` — create user
- `POST /api/auth/login` — JWT bearer token (form-urlencoded)
- `GET /api/auth/me` — current user
- `POST /api/auth/logout`

### Documents (Form 16)
- `POST /api/documents/upload` — upload Form 16 (PDF/image), returns `form16_id` and extracted fields when confidence ≥ 0.25, otherwise `extraction_status: "review_required"`

### Indian tax filing (Phase 0 / 2 / 3)
- `POST /api/v2/calc/preview` — stateless tax computation (regime, gross_income, deductions)
- `POST /api/v2/filing/start` — manual entry **or** `form16_id`; persists `ITR1Filing`, writes PDF, returns `filing_id`. Optional `client_id` routes WS progress events.
- `GET /api/v2/filing/{id}/pdf` — download ITR-1 PDF
- `GET /api/v2/filing/{id}/json` — IT Dept ITR-1 JSON
- `GET /api/v2/filing/{id}/status` — filing summary

### LangGraph chat workflow
- `POST /api/v2/filing/chat/start` — start a thread; runs interviewer → researcher → calculator → auditor
- `POST /api/v2/filing/chat/message` — continue a thread

### WebSocket
- `/api/ws/{client_id}` — receive `filing.starting / filing.calculating / filing.complete` and agent activity events

Full schema: `http://localhost:8000/api/docs`.

---

## Documentation

### Getting Started
- [`docs/setup/QUICKSTART_DATABASE.md`](docs/setup/QUICKSTART_DATABASE.md) — Postgres + pgvector setup
- [`docs/setup/POSTGRESQL_INSTALLATION_WINDOWS.md`](docs/setup/POSTGRESQL_INSTALLATION_WINDOWS.md) — Windows-specific notes
- [`docs/setup/POSTGRESQL_SETUP.md`](docs/setup/POSTGRESQL_SETUP.md) — manual setup

### API & Architecture
- [`docs/api/API_REFERENCE.md`](docs/api/API_REFERENCE.md) — endpoint reference
- [`docs/api/AGENT_SYSTEM_SUMMARY.md`](docs/api/AGENT_SYSTEM_SUMMARY.md) — LangGraph nodes
- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) — directory map

### Design / Plans
- [`docs/superpowers/specs/2026-04-30-indian-tax-data-pipeline-design.md`](docs/superpowers/specs/2026-04-30-indian-tax-data-pipeline-design.md) — design spec
- [`docs/superpowers/specs/2026-04-30-broken-pipelines-and-fixes.md`](docs/superpowers/specs/2026-04-30-broken-pipelines-and-fixes.md) — pre-migration audit
- [`docs/superpowers/plans/2026-04-30-indian-tax-data-pipeline-phase0.md`](docs/superpowers/plans/2026-04-30-indian-tax-data-pipeline-phase0.md) — Phase 0 implementation plan
- [`docs/MIGRATION_NOTES.md`](docs/MIGRATION_NOTES.md) — what changed (US → India)

### Guides
- [`docs/guides/RAG_KNOWLEDGE_BASE.md`](docs/guides/RAG_KNOWLEDGE_BASE.md) — extending the ITR rulebook
- [`docs/guides/UPDATING_FOR_NEW_FY.md`](docs/guides/UPDATING_FOR_NEW_FY.md) — what to change when slabs / Finance Act updates land
- [`docs/api/AUTHENTICATION.md`](docs/api/AUTHENTICATION.md) — JWT login flow for API consumers

---

## Migration Notes (US → India)

This project was originally scaffolded as a US tax-filing prototype (W-2, 1099, IRS, ChromaDB, AutoGen). It has been fully migrated to Indian tax filing. See [`docs/MIGRATION_NOTES.md`](docs/MIGRATION_NOTES.md) for the complete changelog.

**Removed**
- `W2Form`, `Form1099`, `Dependent`, `TaxForm` tables
- `app/autogen_agents/` directory and `pyautogen` dependency
- `public/llm-tax-knowledge.txt`, root `LLM.txt` (US IRS content)
- `app/api/filing.py`, `app/api/tax_forms.py` (US-flavored)
- US-flavored frontend brackets and filing-status enums in `taxCalculationTools.ts`

**Added**
- `Form16`, `ITR1Filing`, `RagDocument` tables; `pan_encrypted` / `aadhaar_encrypted` on `User`
- `services/tax_engine_in.py` deterministic Indian tax engine
- `services/itr1_json_builder.py`, `services/form16_extractor.py`
- `rag/ingest.py` + `rag/retriever.py` over **pgvector** (cosine similarity)
- `/api/v2/calc/preview`, `/api/v2/filing/start`, `/api/v2/filing/{id}/pdf|json|status`, `/api/v2/filing/chat/{start,message}`
- WebSocket `filing.starting / filing.calculating / filing.complete` events keyed to `client_id`

**Out of scope (later)**
- Real IT Dept PDF ingestion (Income Tax Act, ITR-1 instructions, Finance Act 2024). Currently uses curated `tax_rules.txt`.
- E-filing submission to incometax.gov.in
- AsyncPostgresSaver for LangGraph checkpointing (currently in-memory)
- Full frontend audit of `complianceTools.ts`, `advisoryTools.ts` (off the data-pipeline path)

---

## Contributing

1. Branch from `develop`
2. Follow existing patterns (PEP 8 backend, Vue 3 Composition API frontend)
3. Run `python -m pytest tests/ -q` from `backend/` — all 75 tests must pass
4. Open a PR against `develop`

---

## License

Educational purposes. See LICENSE file.
