# Project Structure Overview

This document describes the layout of the **Indian Tax Filing AI Agent** repository (Phase 0–8, FY 2024-25).

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
│   │                                 #   startup: vector extension, create_all, open_graph_pool, RAG prewarm
│   ├── database.py                   # SQLAlchemy engine, get_db, Base
│   ├── models.py                     # 7 tables + UserRole enum (filer/helper/read_only)
│   ├── schemas.py                    # Pydantic request/response (User, UserProfile, Auth, Health)
│   ├── crud.py                       # User / UserProfile / AuditLog CRUD
│   ├── security.py                   # JWT + bcrypt + AES (Fernet) for PAN/Aadhaar
│   │
│   ├── api/                          # REST + WebSocket routers
│   │   ├── auth.py                   # /api/auth/{register, login, me, logout}
│   │   ├── users.py                  # /api/users/{me, me/profile, ...}
│   │   ├── documents.py              # /api/documents/upload (Tesseract OCR + Form 16 extraction)
│   │   ├── filing_v2.py              # /api/v2/calc/preview, /api/v2/filing/*
│   │   │                             #   filing/start gated by require_role(filer, helper)
│   │   ├── explain.py                # /api/v2/explain/{/, whatif, regime-compare} — XAI
│   │   ├── behavior.py               # POST /api/users/behavior — adaptive engine input
│   │   ├── deps.py                   # require_role(*roles) RBAC dependency factory
│   │   ├── ws.py                     # /api/ws/{client_id} (per-client filing.* events)
│   │   └── sdui.py                   # /api/sdui/dashboard/{user_id}
│   │
│   ├── agents_v2/                    # LangGraph workflow (sole agent system — AutoGen retired)
│   │   ├── graph.py                  # StateGraph + AsyncPostgresSaver + pool management
│   │   │                             #   open_graph_pool() / close_graph_pool() wired into lifespan
│   │   ├── state.py                  # TaxFilingState TypedDict (regime, form16_id, tax_breakdown, ...)
│   │   └── nodes.py                  # interviewer / researcher / calculator / auditor
│   │
│   ├── rag/                          # pgvector-backed RAG
│   │   ├── ingest.py                 # SentenceTransformer + paragraph chunking + DB writes
│   │   └── retriever.py              # cosine_distance similarity search with optional topic_filter
│   │
│   ├── services/
│   │   ├── tax_engine_in.py          # Deterministic Indian tax engine (sole source of tax math)
│   │   │                             #   compute_filing(gross_income, deductions, regime, is_salary_income, fy, age)
│   │   ├── tax_engine_in_constants.py # FY 2024-25 slabs, 87A, surcharge bands, 80C/80D, cess
│   │   │                             #   senior (60+) and super-senior (80+) old-regime exemptions
│   │   ├── xai_engine.py             # XAI: explain_breakdown(), what_if(), compare_regimes()
│   │   │                             #   LineExplanation, ExplanationResult, CounterfactualResult dataclasses
│   │   ├── adaptive_engine.py        # EMA cognitive load scoring; process_event() → AdaptiveDecision
│   │   │                             #   weights: error_rate 40%, slow_typing 30%, help_clicks 30%
│   │   │                             #   thresholds: load < 0.20 → suggest expert; load > 0.50 → novice
│   │   ├── itr1_json_builder.py      # IT Department ITR-1 JSON shape
│   │   ├── pdf_generator.py          # ITR-1 PDF (ReportLab, INR Indian grouping)
│   │   ├── form16_extractor.py       # Regex-based parser with Form16Data Pydantic schema
│   │   └── ocr.py                    # Tesseract wrapper (PDF + image)
│   │
│   ├── websockets/manager.py         # ConnectionManager with per-client_id routing
│   └── sdui/                         # Adaptive-UI schema (UIComponent, UISchema)
│
├── scripts/
│   ├── recreate_db.py                # CREATE EXTENSION vector + drop_all + create_all
│   └── scraper.py                    # incometax.gov.in scraper for RAG ingestion
│                                     #   chunk_heading_hash, build_chunk_header, parse_html_page,
│                                     #   parse_pdf_bytes, deduplicate_chunks, fetch_url, scrape()
│
├── tests/                            # 88 tests, 0 warnings
│   ├── test_tax_engine.py            # Senior/super-senior citizen slab tests (13)
│   ├── test_xai_engine.py            # XAI engine unit tests (5)
│   ├── test_adaptive_engine.py       # Adaptive engine unit tests (7)
│   ├── test_metamorphic.py           # 25 metamorphic invariants (property-based)
│   ├── services/test_tax_engine_in.py # Core tax engine: slabs, deductions, rebate, surcharge, cess (33)
│   ├── scripts/test_scraper.py       # Scraper utilities (5)
│   └── conftest.py                   # SQLite in-memory + StaticPool db_session fixture
│
├── tax_rules.txt                     # Curated FY 2024-25 rulebook (29 sections, Phase 1 RAG corpus)
├── pytest.ini
├── requirements.txt
├── .env.dev / .env.prod / .env.example
└── venv/                             # Python virtual environment (never use system pip)
```

### Database schema (7 tables)

```sql
-- Users & profile
users               -- email, hashed_password, full_name, pan_encrypted, aadhaar_encrypted,
                    -- role userrole NOT NULL DEFAULT 'filer'
user_profiles       -- preferred_mode ('novice'|'intermediate'|'expert'),
                    -- preferred_regime ('old'|'new'), theme, notifications_enabled,
                    -- filing_history (JSON), behavioral EMA scores

-- Indian tax filing data
form16              -- Extracted Form 16 records (one per uploaded document)
itr1_filings        -- Computed ITR-1 (regime, breakdown, itr1_json, pdf_path, status,
                    -- age_category 'general'|'senior'|'super_senior')

-- Compliance & audit
compliance_checks   -- Per-filing audit results (FK -> itr1_filings)
audit_logs          -- User action history

-- RAG
rag_documents       -- pgvector embeddings of the IT rulebook (Vector(384), cosine distance)
```

**Relationships**:
- `users` 1↔1 `user_profiles`
- `users` 1↔N `form16`
- `users` 1↔N `itr1_filings`
- `form16` 1↔N `itr1_filings`
- `itr1_filings` 1↔N `compliance_checks`
- `users` 1↔N `audit_logs`

See [`backend/app/models.py`](../backend/app/models.py) for the canonical column list.

---

## Frontend (`src/`)

> **Important**: `.tsx` files under `src/components/` are orphaned React legacy scaffolding that do NOT render in the live app. The active UI uses `.vue` files under `src/components-vue/` and `src/pages/`.

```
src/
├── main.ts                           # Vue app entry point (createApp + Pinia + Router)
├── router.ts                         # 15 routes (3 public, 12 auth-guarded)
│
├── pages/
│   ├── LandingPage.vue               # Public home — AI feature showcase (XAI, adaptive, senior slabs)
│   ├── Login.vue, Register.vue       # Auth pages
│   ├── Index.vue                     # Dashboard
│   ├── Reports.vue                   # Tax reports + XAI explanation panel
│   │                                 #   (line items, what-if inputs, regime compare tab)
│   ├── Filings.vue                   # Filing list + PDF/JSON download
│   ├── Chat.vue                      # LangGraph chat + RAG sources sidebar
│   │                                 #   (read_only role gate, behavioral tracking)
│   ├── Documents.vue                 # Form 16 upload → agentStore.form16Data prefill
│   ├── NewFiling.vue                 # Manual entry (prefilled from Form 16 if uploaded)
│   ├── WizardFiling.vue              # Guided step-by-step filing (behavioral event tracking)
│   ├── FilingGrid.vue                # Expert grid view
│   ├── Settings.vue                  # Profile (name/email) + Preferences (regime/mode/theme)
│   ├── Help.vue, Contact.vue         # Support pages
│   └── NotFound.vue                  # 404
│
├── components-vue/
│   ├── adaptive/
│   │   └── ModeSwitcher.vue          # novice / intermediate / expert switcher (3 modes)
│   ├── navigation/BackButton.vue
│   └── ui/                           # Radix Vue primitives (Card, Input, Button, Select, ...)
│
├── composables/
│   └── useSdui.ts                    # fetchFormSchema() / fetchDashboardSchema() using native fetch
│
├── stores/
│   ├── authStore.ts                  # JWT token + user state (Pinia)
│   ├── agentStore.ts                 # Form16Data interface + form16Data ref
│   ├── uiStore.ts                    # mode ('novice'|'intermediate'|'expert'), setMode()
│   └── chatStore.ts                  # Chat message history
│
├── agents/tools/
│   ├── taxCalculationTools.ts        # Thin client over /api/v2/calc/preview (India-aligned)
│   ├── complianceTools.ts            # (cleanup backlog — still has US thresholds)
│   └── advisoryTools.ts              # (idem)
│
└── assets/                           # Static assets (images, fonts)
```

---

## Documentation (`docs/`)

```
docs/
├── README.md                          # Documentation index
├── MIGRATION_NOTES.md                 # US -> India changelog
├── PROJECT_STRUCTURE.md               # You are here
├── BACKEND_STATUS.md                  # Current phase status + test breakdown
│
├── setup/
│   ├── QUICKSTART_DATABASE.md         # Postgres + pgvector setup
│   ├── POSTGRESQL_INSTALLATION_WINDOWS.md
│   └── POSTGRESQL_SETUP.md
│
├── api/
│   ├── API_REFERENCE.md               # REST API reference (all endpoints)
│   ├── AUTHENTICATION.md              # JWT login flow
│   └── AGENT_SYSTEM_SUMMARY.md        # Frontend Pinia + agent store
│
├── guides/
│   ├── RAG_KNOWLEDGE_BASE.md          # Extending the ITR rulebook
│   └── UPDATING_FOR_NEW_FY.md         # What to change for a new fiscal year
│
└── superpowers/                       # Design artefacts (specs + plans)
    ├── specs/2026-05-09-gap-fix-design.md
    └── plans/                         # Agent implementation plans (0–8)
```

---

## Data flow

```
                              ┌─ /api/v2/calc/preview ──────────────┐
                              │  (stateless preview)                │
User input (Vue + Pinia)      │                                     ▼
        │                     │                            tax_engine_in
        ▼                     │                            (deterministic)
taxCalculationTools.ts ───────┘                                     │
                                                    ┌───────────────┴──────────┐
                                                    │  TaxBreakdown            │
                                                    └───────────────┬──────────┘
                                                                    │
                                                    ┌───────────────▼──────────┐
                                                    │  xai_engine              │
                                                    │  explain / what_if /     │
                                                    │  compare_regimes         │
                                                    └──────────────────────────┘

POST /api/v2/filing/start (manual or form16_id):
  └─ tax_engine_in ─▶ build_itr1_json ─▶ itr1_filings row + PDF
                                         │
                           WS events ───▶ /api/ws/{client_id}

POST /api/users/behavior:
  └─ adaptive_engine.process_event() ─▶ AdaptiveDecision (mode suggestion)

LangGraph chat path:
  HumanMessage ─▶ interviewer (EXTRACTION: JSON)
                       │
                       ▼
                  researcher ──pgvector cosine─▶ rag_documents
                       │
                       ▼
                  calculator ──tax_engine_in──▶ TaxBreakdown
                       │
                       ▼
                   auditor (25 invariants) ──▶ audit_status
                       │
                       ▼
                      END ──▶ ChatResponse
              (thread saved to Postgres via AsyncPostgresSaver)
```

---

## File count summary

| Category | Count | Notes |
|---|---|---|
| Python source files | 35+ | backend/app/ + scripts |
| Backend tests | 88 | 0 warnings, 6 test files |
| TypeScript / Vue files | 60+ | src/pages, components-vue, stores, composables |
| Database tables | 7 | All India-aligned + UserRole enum |
| LangGraph nodes | 4 | interviewer, researcher, calculator, auditor |
| Tax-engine pure functions | 6 | compute_slab_tax, apply_deductions, apply_rebate_87a, compute_surcharge, compute_cess, compute_filing |
| REST routes | 21 | including 9 under /api/v2/ |
| Metamorphic invariants | 25 | monotonicity, composition, regime rules, senior exemptions, etc. |

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
| FY 2024-25 constants | `backend/app/services/tax_engine_in_constants.py` |
| XAI engine | `backend/app/services/xai_engine.py` |
| Adaptive engine | `backend/app/services/adaptive_engine.py` |
| RBAC dependency | `backend/app/api/deps.py` |
| ITR-1 JSON output | `backend/app/services/itr1_json_builder.py` |
| ITR-1 PDF output | `backend/app/services/pdf_generator.py` |
| Form 16 extraction | `backend/app/services/form16_extractor.py` |
| pgvector RAG | `backend/app/rag/ingest.py`, `backend/app/rag/retriever.py` |
| LangGraph workflow | `backend/app/agents_v2/graph.py`, `nodes.py`, `state.py` |
| REST endpoints | `backend/app/api/filing_v2.py`, `explain.py`, `behavior.py`, `auth.py` |
| WebSocket events | `backend/app/api/ws.py`, `backend/app/websockets/manager.py` |
| Web scraper | `backend/scripts/scraper.py` |
| Frontend tax tools | `src/agents/tools/taxCalculationTools.ts` |
| SDUI composable | `src/composables/useSdui.ts` |
| UI mode store | `src/stores/uiStore.ts` |
| Reports + XAI panel | `src/pages/Reports.vue` |
| RAG ingestion | `python -m app.rag.ingest` |

---

**Setup**: [`setup/QUICKSTART_DATABASE.md`](setup/QUICKSTART_DATABASE.md)
**REST API**: [`api/API_REFERENCE.md`](api/API_REFERENCE.md)
**Migration changelog**: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md)
