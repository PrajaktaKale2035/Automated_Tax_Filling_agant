# Project Structure Overview

This document describes the layout of the **Indian Tax Filing AI Agent** repository after the US-to-India migration (commits `63927e5`, `9bead04`, `2429d40`, `0e8debf`).

---

## High-level architecture

```
Automated_Tax_Filling_agant/
├── backend/             # FastAPI + SQLAlchemy + LangGraph + pgvector RAG
├── src/                 # Vue 3 frontend
├── docs/                # Documentation (this folder)
├── public/              # Static assets
├── docker-compose.yml   # Postgres (pgvector image), pgAdmin, Neo4j (optional)
└── package.json
```

---

## Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py                       # FastAPI app + lifespan + CORS + exception handlers
│   ├── database.py                   # SQLAlchemy engine, get_db, Base, init_db
│   ├── models.py                     # 7 tables (Indian schema, see below)
│   ├── schemas.py                    # Pydantic request/response (User, UserProfile, Auth, Health)
│   ├── crud.py                       # User / UserProfile / AuditLog / authenticate_user
│   ├── security.py                   # JWT + bcrypt + AES (Fernet) for PAN/Aadhaar
│   │
│   ├── api/                          # REST + WebSocket routers
│   │   ├── auth.py                   # /api/auth/{register, login, me, logout}
│   │   ├── users.py                  # /api/users/{me, me/profile, ...}
│   │   ├── documents.py              # /api/documents/upload (Tesseract OCR + Form 16 extraction)
│   │   ├── filing_v2.py              # /api/v2/calc/preview, /api/v2/filing/*
│   │   ├── ws.py                     # /api/ws/{client_id} (per-client filing.* events)
│   │   └── sdui.py                   # /api/sdui/dashboard/{user_id}
│   │
│   ├── agents_v2/                    # LangGraph workflow (sole agent system - AutoGen retired)
│   │   ├── graph.py                  # StateGraph + InMemorySaver
│   │   ├── state.py                  # TaxFilingState TypedDict (with regime, form16_id, tax_breakdown, ...)
│   │   └── nodes.py                  # interviewer / researcher / calculator / auditor
│   │
│   ├── rag/                          # pgvector-backed RAG (replaces ChromaDB)
│   │   ├── ingest.py                 # SentenceTransformer + paragraph chunking + DB writes
│   │   └── retriever.py              # cosine_distance similarity search with optional topic_filter
│   │
│   ├── services/
│   │   ├── tax_engine_in.py          # Deterministic Indian tax engine (sole source of tax math)
│   │   ├── tax_engine_in_constants.py # FY 2024-25 slabs, 87A, surcharge bands, 80C/80D, cess
│   │   ├── itr1_json_builder.py      # IT Department ITR-1 JSON shape
│   │   ├── pdf_generator.py          # ITR-1 PDF (ReportLab, INR Indian grouping)
│   │   ├── form16_extractor.py       # Regex-based parser with Form16Data Pydantic schema
│   │   └── ocr.py                    # Tesseract wrapper (PDF + image)
│   │
│   ├── websockets/manager.py         # ConnectionManager with per-client_id routing
│   └── sdui/                         # Adaptive-UI schema (UIComponent, UISchema)
│
├── scripts/
│   └── recreate_db.py                # CREATE EXTENSION vector + drop_all + create_all
│
├── tests/                            # 75 tests, 0 warnings
│   ├── api/test_filing_v2_phase0.py  # /calc/preview, /filing/start, downloads, 404s (11)
│   ├── api/test_ws_phase3.py         # WebSocket connect/echo/filing.complete (3)
│   ├── integration/test_phase0_e2e.py # calculator + auditor + full-pipeline (6)
│   ├── rag/test_pgvector_rag.py      # Live pgvector retrieval (4; skips if Postgres down)
│   ├── services/                     # tax_engine (33), form16 (8), itr1_json (3), pdf (2)
│   ├── test_metamorphic.py           # Hypothesis property-based tests (5)
│   └── conftest.py                   # SQLite in-memory + StaticPool db_session fixture
│
├── tax_rules.txt                     # Curated FY 2024-25 rulebook (Phase 1 RAG corpus)
├── pytest.ini
├── requirements.txt                  # Pinned deps (Python 3.10-3.12); 3.14 needs >= versions
├── .env.dev / .env.prod
└── chroma_db/                        # Legacy (gitignored). Safe to delete - no longer used.
```

### Database schema (7 tables)

```sql
-- Users & profile
users               -- email, hashed_password, full_name, pan_encrypted, aadhaar_encrypted
user_profiles      -- adaptive UI mode, preferred_regime ('old'|'new'), filing_history (JSON)

-- Indian tax filing data
form16              -- Extracted Form 16 records (one per uploaded document)
itr1_filings        -- Computed ITR-1 (regime, breakdown, itr1_json, pdf_path, status)

-- Compliance & RAG
compliance_checks   -- Per-filing audit results (FK -> itr1_filings)
audit_logs          -- User action history
rag_documents       -- pgvector embeddings of the IT rulebook (Vector(384), cosine)
```

**Relationships**:
- `users` 1↔1 `user_profiles`
- `users` 1↔N `form16`
- `users` 1↔N `itr1_filings`
- `form16` 1↔N `itr1_filings` (a filing can reference its source Form 16)
- `itr1_filings` 1↔N `compliance_checks`
- `users` 1↔N `audit_logs`

See [`backend/app/models.py`](../backend/app/models.py) for the canonical column list.

---

## Frontend (`src/`)

```
src/
├── agents/                           # Frontend AI agent system (LangChain.js)
│   ├── BaseAgent.ts
│   ├── configs.ts
│   ├── langchain/                    # LangChain integration
│   │   ├── LangChainAgent.ts
│   │   ├── LangChainTools.ts
│   │   └── WorkflowOrchestrator.ts
│   ├── llm/                          # OpenAI / Anthropic / Gemini providers
│   ├── specialized/                  # OrchestratorAgent, TaxCalculatorAgent, ...
│   └── tools/
│       ├── taxCalculationTools.ts    # Indian: thin client over /api/v2/calc/preview
│       ├── complianceTools.ts        # (still has US thresholds - on the cleanup backlog)
│       ├── advisoryTools.ts          # (idem)
│       ├── documentProcessingTools.ts
│       └── formFillingTools.ts
│
├── pages/
│   ├── Filings.vue, FilingGrid.vue
│   ├── WizardFiling.vue
│   ├── Documents.vue
│   ├── Reports.vue                   # Indian deductions (80C, std, 80D, HRA)
│   ├── Settings.vue, Help.vue, ...
│
├── components-vue/
│   ├── chat/                         # Chat UI
│   ├── inputs/                       # Form inputs
│   ├── adaptive/                     # Mode-aware components
│   ├── analysis/RealTimeAnalysis.vue # Indian deductions, INR formatting
│   ├── export/TaxReportExporter.vue  # ITR-1 HTML + CSV templates (FY 2024-25 slabs)
│   └── ui/                           # Radix Vue primitives
│
├── stores/                           # Pinia
│   ├── chatStore.ts, agentStore.ts
│   └── ...
│
├── data/                             # Tax knowledge utilities
├── router.ts
└── main.ts
```

---

## Documentation (`docs/`)

```
docs/
├── README.md                          # This index
├── MIGRATION_NOTES.md                 # US -> India changelog (read this first)
├── PROJECT_STRUCTURE.md               # You are here
├── BACKEND_STATUS.md                  # Backend phase status
├── IMPLEMENTATION_PLAN.md             # Historical implementation plan
│
├── setup/
│   ├── QUICKSTART_DATABASE.md         # Postgres + pgvector setup (UPDATED for migration)
│   ├── POSTGRESQL_INSTALLATION_WINDOWS.md
│   └── POSTGRESQL_SETUP.md
│
├── api/
│   ├── API_REFERENCE.md               # REST API reference (UPDATED - Phase 0/1/2/3 endpoints)
│   ├── AGENT_SYSTEM_SUMMARY.md        # Frontend Pinia + agent store
│   └── LLM_PROVIDERS_IMPLEMENTATION.md
│
├── guides/
│   ├── LANGCHAIN_INTEGRATION.md
│   ├── LANGCHAIN_QUICKSTART.md
│   └── HOW_TO_SWITCH_PROVIDERS.md
│
└── superpowers/                       # Design artefacts
    ├── specs/2026-04-30-indian-tax-data-pipeline-design.md
    ├── specs/2026-04-30-broken-pipelines-and-fixes.md
    └── plans/2026-04-30-indian-tax-data-pipeline-phase0.md
```

---

## Data flow (Phase 0–4)

```
                                    ┌─ /api/v2/calc/preview ─────────┐
                                    │  (stateless preview)           │
User input (Vue + Pinia)            │                                ▼
        │                           │                       tax_engine_in
        ▼                           │                       (deterministic)
taxCalculationTools.ts ─────────────┘                                │
        │                                                            │
        ▼                                              ┌─────────────┴─────────┐
POST /api/v2/calc/preview  ◄─────────────────────────► │  TaxBreakdown         │
                                                      └───────────────────────┘

                  ┌──────────────────────────────────────────────────────┐
                  │ POST /api/v2/filing/start (manual or form16_id)      │
                  └──────┬─────────┬─────────────────────────────────────┘
                         │         │
              load Form16│         │compute via tax_engine_in
                  (if id)│         ▼
                         │   build_itr1_json()  ───▶  itr1_filings.itr1_json
                         │   generate_itr1_pdf() ─▶  itr1_filings.pdf_path
                         ▼
                    form16 row
                         │
                         │ WS events (filing.starting, .calculating, .complete)
                         ▼
              /api/ws/{client_id}  ────▶  Frontend listener


LangGraph chat path (POST /api/v2/filing/chat/start):
  HumanMessage ─▶ interviewer  (extracts profile via JSON marker)
                       │
                       ▼
                  researcher  ──pgvector cosine─▶ rag_documents
                       │
                       ▼
                  calculator  ──tax_engine_in──▶ TaxBreakdown
                       │
                       ▼
                   auditor    (5 invariants)  ──▶ audit_status / errors
                       │
                       ▼
                      END  ──▶ ChatResponse
```

---

## File count summary

| Category | Count | Notes |
|---|---|---|
| Python source files | 30+ | backend/app/ + scripts |
| Backend tests | 75 | 0 warnings |
| TypeScript files | 50+ | src/agents and tools |
| Vue components | 40+ | src/components-vue and pages |
| Database tables | 7 | All India-aligned |
| LangGraph nodes | 4 | interviewer, researcher, calculator, auditor |
| Tax-engine pure functions | 6 | compute_slab_tax, apply_deductions, apply_rebate_87a, compute_surcharge, compute_cess, compute_filing |
| Public REST routes | 19 | including 6 under /api/v2/ |

---

## Naming conventions

**Backend (Python)**
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`
- Test files: `test_<unit>.py`

**Frontend (TypeScript / Vue)**
- Files: `PascalCase.vue`, `camelCase.ts`
- Composition functions: `camelCase()`
- Stores: `useXxxStore` (Pinia convention)

**Database**
- Tables / columns: `snake_case`
- Foreign keys: `<table>_id`

---

## Quick navigation

| Feature | Location |
|---|---|
| Database schema | `backend/app/models.py` |
| Tax math (engine) | `backend/app/services/tax_engine_in.py` |
| ITR-1 JSON output | `backend/app/services/itr1_json_builder.py` |
| ITR-1 PDF output | `backend/app/services/pdf_generator.py` |
| Form 16 extraction | `backend/app/services/form16_extractor.py` |
| pgvector RAG | `backend/app/rag/ingest.py`, `backend/app/rag/retriever.py` |
| LangGraph workflow | `backend/app/agents_v2/graph.py`, `nodes.py`, `state.py` |
| REST endpoints | `backend/app/api/filing_v2.py`, `documents.py`, `auth.py` |
| WebSocket events | `backend/app/api/ws.py`, `backend/app/websockets/manager.py` |
| Frontend tax tools | `src/agents/tools/taxCalculationTools.ts` |
| ITR-1 PDF/CSV export | `src/components-vue/export/TaxReportExporter.vue` |
| Reports page | `src/pages/Reports.vue` |
| Schema migration | `backend/scripts/recreate_db.py` |
| RAG ingestion | `python -m app.rag.ingest` |

---

**Migration changelog**: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md)
**Setup**: [`setup/QUICKSTART_DATABASE.md`](setup/QUICKSTART_DATABASE.md)
**REST API**: [`api/API_REFERENCE.md`](api/API_REFERENCE.md)
