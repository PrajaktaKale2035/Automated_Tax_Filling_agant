# Indian Tax Filing AI Agent — Automated ITR-1 Assistant

An intelligent, autonomous AI agent system for **Indian income tax filing (ITR-1 Sahaj)** built with **Vue 3**, **FastAPI**, **PostgreSQL + pgvector**, and **LangGraph multi-agent orchestration**.

> **Status**: Phase 0–8 complete. **Tax Year**: FY 2024-25 / AY 2025-26. **Form**: ITR-1 (salary + interest income). **Tests**: 88 passing.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Documentation](#documentation)

---

## Overview

This project is an autonomous Indian tax filing system. It:

- **Extracts data from Form 16** (Indian salary TDS certificate) via Tesseract OCR + a Pydantic-backed extractor
- **Calculates ITR-1 tax** through a deterministic engine in `backend/app/services/tax_engine_in.py` (no LLM math) — slabs, standard deduction, 80C, 80D, rebate u/s 87A, surcharge bands, 4% Health & Education Cess; senior citizen and super-senior citizen exemptions
- **Explains every tax line** via an XAI engine — plain-language explanations, what-if counterfactuals (e.g. "if I add ₹50,000 to 80C"), and old-vs-new regime comparison
- **Adapts the UI** in real time based on measured cognitive load (error rate, typing speed, help-click rate) using an EMA-weighted scoring model
- **Validates the filing** with 25 metamorphic invariants (totals consistency, non-negativity, regime rules, surcharge bands)
- **Compares old vs new regime** and surfaces the lower-tax option with a structured breakdown
- **Produces ITR-1 outputs** — IT Department-shaped JSON and a rendered PDF in ITR-1 layout
- **Grounds advice in the rulebook** via pgvector RAG over the Income Tax Act / ITR-1 instructions
- **Runs a chat-driven workflow** through LangGraph: interviewer → researcher → calculator → auditor

---

## Features

### Multi-agent system (LangGraph)

- **Interviewer** — extracts structured fields (`income_salary`, `regime`, `deductions_80c/80d`, `pan`, `age`, ...) from natural-language conversation via `EXTRACTION:` JSON
- **Researcher** — runs cosine-similarity RAG over the `rag_documents` pgvector table using `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Calculator** — invokes the deterministic `tax_engine_in` (never asks the LLM to do arithmetic)
- **Auditor** — validates the resulting `TaxBreakdown` against 25 metamorphic invariants
- **Persistence** — LangGraph threads saved to PostgreSQL via `AsyncPostgresSaver` (survives restart)

### Deterministic Indian tax engine (`tax_engine_in`)

- New regime slabs (FY 2024-25): 0/5/10/15/20/30 across ₹3L–₹15L+
- Old regime slabs: 0/5/20/30 across ₹2.5L–₹10L+; ₹3L basic exemption for senior citizens (60+); ₹5L exemption for super-senior citizens (80+)
- Standard deduction: ₹75,000 (new) / ₹50,000 (old)
- Section 80C cap ₹1.5L, 80D cap ₹25,000 (old regime only)
- Rebate u/s 87A: ₹25,000 if income ≤ ₹7L (new) / ₹12,500 if income ≤ ₹5L (old)
- Surcharge bands: 10/15/25/37% (new regime caps at 25%)
- 4% Health & Education Cess on (tax + surcharge)

### Explainable AI (XAI engine)

- **Line-by-line explanations** — every component of the tax breakdown gets a plain-language sentence
- **What-if analysis** — "what if I increase 80C by ₹X?" recomputes the full breakdown and shows the delta
- **Regime comparison** — side-by-side old vs new with the lower-tax option highlighted

### Adaptive UI engine

- EMA-weighted cognitive load score from three signals: error rate (40%), slow typing (30%), help clicks (30%)
- Score thresholds: `load < 0.20` → suggest expert mode; `load > 0.50` → suggest novice mode
- Mode is persisted on `user_profiles.preferred_mode` and respected across sessions

### Data pipeline

- **Document upload** → Tesseract OCR → Form 16 detection → Pydantic structured extraction → `form16` row
- **Filing path** (manual or Form 16) → tax engine → `itr1_filings` row → ITR-1 JSON + PDF
- **WebSocket events** — clients receive `filing.starting → filing.calculating → filing.complete` keyed to `client_id`
- **Web scraper** — `backend/scripts/scraper.py` fetches and chunks content from `incometax.gov.in` for RAG ingestion

### Storage

- **PostgreSQL 16 + pgvector extension** for both relational data and embeddings
- 7 tables: `users`, `user_profiles`, `form16`, `itr1_filings`, `compliance_checks`, `audit_logs`, `rag_documents`

### Security & access control

- JWT authentication, bcrypt password hashing
- Encrypted PAN and Aadhaar fields on `User` (via `app.security` Fernet AES)
- Role-based access control: `UserRole.filer / helper / read_only` on `User.role`
- `require_role()` FastAPI dependency factory in `api/deps.py`

### Adaptive UI (Vue 3)

- Three modes (novice / intermediate / expert) tracked via `UserProfile.preferred_mode`
- Frontend `taxCalculationTools.ts` calls `/api/v2/calc/preview` so the same engine drives live preview, the LangGraph calculator, and the PDF
- XAI explanation panel in Reports page — line items, what-if inputs, regime compare tab

---

## Tech Stack

### Frontend
- Vue 3 (Composition API) + TypeScript
- Vite (port 8080), Pinia, Vue Router
- TailwindCSS, Radix Vue, Lucide Vue
- LangChain.js for agent tooling (calls backend for tax math)

### Backend
- Python 3.10+ (tested on 3.14), FastAPI
- SQLAlchemy 2.0, Pydantic v2
- PostgreSQL 16 (`pgvector/pgvector:pg16` Docker image)
- LangGraph + LangChain (multi-provider: OpenAI / Gemini / Ollama)
- `langgraph-checkpoint-postgres` — `AsyncPostgresSaver` for durable thread state
- ReportLab (ITR-1 PDF rendering)
- httpx + beautifulsoup4 + pdfplumber (web scraper)
- pytest + hypothesis (88 tests, 0 warnings)

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

# Ingest the curated Indian rulebook into pgvector
python -m app.rag.ingest

# Run the API
python -m uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`. Docs at `http://localhost:8000/api/docs`. OpenAPI schema at `/api/openapi.json`.

> **LLM key**: copy `backend/.env.dev` to `backend/.env` and set `LLM_PROVIDER` + the matching API key (Gemini, OpenAI, or Ollama) if you want the LangGraph chat flow (`/api/v2/filing/chat/start`). The deterministic endpoints (`/api/v2/calc/preview`, `/api/v2/filing/start`, `/api/v2/explain/*`) work without any LLM. See `PHASE1_SETUP.md` for all provider options.

### 3. Frontend setup

```bash
npm install
npm run dev
```

Frontend at `http://localhost:8080`.

### 4. Smoke test

```bash
# Indian new-regime preview — full Section 87A rebate
curl -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income": 600000, "deductions": {}, "regime": "new", "is_salary_income": true}'
# -> total_tax: 0

# XAI explanation
curl -X POST http://localhost:8000/api/v2/explain/ \
  -H "Content-Type: application/json" \
  -d '{"gross_income": 1200000, "deductions": {"80c": 100000}, "regime": "new", "age": 30}'
```

---

## Project Structure

```
Automated_Tax_Filling_agant/
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI app + lifespan + CORS
│   │   ├── database.py                   # SQLAlchemy engine, get_db, Base
│   │   ├── models.py                     # 7 tables + UserRole enum
│   │   ├── schemas.py                    # Pydantic request/response models
│   │   ├── crud.py                       # User / UserProfile / AuditLog CRUD
│   │   ├── security.py                   # JWT + bcrypt + AES encryption
│   │   ├── api/
│   │   │   ├── auth.py                   # /api/auth/login, /register, ...
│   │   │   ├── users.py                  # /api/users/...
│   │   │   ├── documents.py              # /api/documents/upload (OCR + Form 16)
│   │   │   ├── filing_v2.py              # /api/v2/calc/* and /api/v2/filing/*
│   │   │   ├── explain.py                # /api/v2/explain/* (XAI endpoints)
│   │   │   ├── behavior.py               # /api/users/behavior (adaptive engine)
│   │   │   ├── deps.py                   # require_role() RBAC dependency
│   │   │   ├── ws.py                     # /api/ws/{client_id} for realtime events
│   │   │   └── sdui.py                   # adaptive-UI dashboard
│   │   ├── agents_v2/                    # LangGraph workflow
│   │   │   ├── graph.py                  # StateGraph + AsyncPostgresSaver + pool management
│   │   │   ├── nodes.py                  # interviewer / researcher / calculator / auditor
│   │   │   └── state.py                  # TaxFilingState TypedDict
│   │   ├── rag/                          # pgvector RAG
│   │   │   ├── ingest.py                 # SentenceTransformer + DB writes
│   │   │   └── retriever.py              # cosine-distance similarity search
│   │   ├── services/
│   │   │   ├── tax_engine_in.py          # deterministic Indian tax engine
│   │   │   ├── tax_engine_in_constants.py # FY 2024-25 slabs / limits / senior exemptions
│   │   │   ├── xai_engine.py             # XAI: explain_breakdown, what_if, compare_regimes
│   │   │   ├── adaptive_engine.py        # EMA cognitive load scoring + mode suggestion
│   │   │   ├── itr1_json_builder.py      # IT Dept ITR-1 JSON shape
│   │   │   ├── pdf_generator.py          # ITR-1 PDF (ReportLab)
│   │   │   ├── form16_extractor.py       # OCR text -> Form16Data
│   │   │   └── ocr.py                    # Tesseract wrapper
│   │   ├── websockets/manager.py         # per-client_id WS routing
│   │   └── sdui/                         # adaptive-UI schema
│   ├── scripts/
│   │   ├── recreate_db.py                # CREATE EXTENSION vector + drop_all + create_all
│   │   └── scraper.py                    # incometax.gov.in scraper for RAG ingestion
│   ├── tests/                            # 88 tests, 0 warnings
│   │   ├── test_tax_engine.py            # senior/super-senior citizen slab tests (13)
│   │   ├── test_xai_engine.py            # XAI engine unit tests (5)
│   │   ├── test_adaptive_engine.py       # adaptive engine unit tests (7)
│   │   ├── test_metamorphic.py           # 25 metamorphic invariants (hypothesis)
│   │   ├── services/test_tax_engine_in.py # core tax engine (33)
│   │   ├── scripts/test_scraper.py       # scraper utility tests (5)
│   │   └── conftest.py                   # SQLite in-memory + StaticPool fixture
│   ├── tax_rules.txt                     # Curated FY 2024-25 rulebook (Phase 1 RAG corpus)
│   └── requirements.txt
├── src/                                  # Vue 3 frontend
│   ├── pages/
│   │   ├── LandingPage.vue               # Public landing (AI feature showcase)
│   │   ├── Index.vue                     # Dashboard
│   │   ├── Reports.vue                   # Tax reports + XAI explanation panel
│   │   ├── Filings.vue                   # Filing list + download
│   │   ├── Chat.vue                      # LangGraph chat + RAG sources sidebar
│   │   ├── Documents.vue                 # Form 16 upload + OCR
│   │   ├── NewFiling.vue                 # Manual filing entry
│   │   ├── WizardFiling.vue              # Guided step-by-step filing
│   │   ├── FilingGrid.vue                # Expert grid view
│   │   └── Settings.vue                  # Profile + preferences
│   ├── components-vue/
│   │   ├── adaptive/ModeSwitcher.vue     # novice / intermediate / expert switcher
│   │   └── ui/                           # Radix Vue primitives
│   ├── composables/useSdui.ts            # SDUI schema fetcher
│   ├── stores/
│   │   ├── authStore.ts                  # JWT token + user state
│   │   ├── agentStore.ts                 # Form 16 data + filing state
│   │   └── uiStore.ts                    # mode + UI preferences (Pinia)
│   └── router.ts                         # 15 routes (public + auth-guarded)
├── docs/
│   ├── setup/                            # database setup
│   ├── api/                              # API reference
│   ├── guides/                           # LangChain / providers
│   └── superpowers/                      # design specs, audit, plans
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

### User & profile
- `GET /api/users/me`, `PUT /api/users/me`
- `GET /api/users/me/profile`, `PUT /api/users/me/profile`
- `POST /api/users/behavior` — record behavioral event for adaptive engine

### Documents (Form 16)
- `POST /api/documents/upload` — upload Form 16 (PDF/image), returns `form16_id` and extracted fields when confidence ≥ 0.25

### Indian tax filing
- `POST /api/v2/calc/preview` — stateless tax computation (regime, gross_income, deductions, age)
- `POST /api/v2/filing/start` — manual entry **or** `form16_id`; requires `filer` or `helper` role
- `GET /api/v2/filing/{id}/pdf` — download ITR-1 PDF
- `GET /api/v2/filing/{id}/json` — IT Dept ITR-1 JSON
- `GET /api/v2/filing/{id}/status` — filing summary

### XAI (Explainable AI)
- `POST /api/v2/explain/` — line-by-line breakdown with plain-language explanations
- `POST /api/v2/explain/whatif` — what-if recompute with delta vs baseline
- `POST /api/v2/explain/regime-compare` — side-by-side old vs new regime

### LangGraph chat workflow
- `POST /api/v2/filing/chat/start` — start a thread; runs interviewer → researcher → calculator → auditor
- `POST /api/v2/filing/chat/message` — continue a thread (state persisted in Postgres via `AsyncPostgresSaver`)

### WebSocket
- `/api/ws/{client_id}` — receive `filing.starting / filing.calculating / filing.complete` and agent activity events

Full schema: `http://localhost:8000/api/docs`.

---

## Documentation

### Getting Started
- [`docs/setup/QUICKSTART_DATABASE.md`](docs/setup/QUICKSTART_DATABASE.md) — Postgres + pgvector setup
- [`docs/setup/POSTGRESQL_INSTALLATION_WINDOWS.md`](docs/setup/POSTGRESQL_INSTALLATION_WINDOWS.md) — Windows-specific notes
- [`PHASE1_SETUP.md`](PHASE1_SETUP.md) — LLM provider configuration

### API & Architecture
- [`docs/api/API_REFERENCE.md`](docs/api/API_REFERENCE.md) — endpoint reference
- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) — directory map
- [`docs/BACKEND_STATUS.md`](docs/BACKEND_STATUS.md) — current status and known gaps

### Guides
- [`docs/guides/RAG_KNOWLEDGE_BASE.md`](docs/guides/RAG_KNOWLEDGE_BASE.md) — extending the ITR rulebook
- [`docs/guides/UPDATING_FOR_NEW_FY.md`](docs/guides/UPDATING_FOR_NEW_FY.md) — what to change when Finance Act updates land
- [`docs/api/AUTHENTICATION.md`](docs/api/AUTHENTICATION.md) — JWT login flow for API consumers
- [`walkthrough.md`](walkthrough.md) — end-to-end system walkthrough

---

## Contributing

1. Branch from `develop`
2. Follow existing patterns (PEP 8 backend, Vue 3 Composition API frontend)
3. Run `python -m pytest tests/ -q` from `backend/` — all 88 tests must pass
4. Open a PR against `develop`

---

## License

Educational purposes. See LICENSE file.
