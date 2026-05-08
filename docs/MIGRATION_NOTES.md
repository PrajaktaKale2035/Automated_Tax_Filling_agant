# Migration Notes — US Tax Scaffolding → Indian ITR-1

This document captures everything that changed when the project was migrated from a US tax-filing prototype to an Indian ITR-1 filing system. Use this as the canonical changelog for anything not derivable from `git log`.

**Date**: 2026-04-30 → 2026-05-01
**Branch**: `develop`
**Tax Year**: FY 2024-25 / AY 2025-26
**Form**: ITR-1 (Sahaj)
**Commits**: `63927e5`, `9bead04`, `2429d40`, `0e8debf`

---

## Domain change

| Before | After |
|---|---|
| US Federal income tax (1040) | Indian income tax (ITR-1 Sahaj) |
| W-2, 1099, dependents, EITC, child tax credit | Form 16, AIS (Phase 2+), 80C/80D, rebate u/s 87A |
| Filing statuses: single / married_joint / married_separate / head_of_household | Filer types: individual / HUF; regimes: old / new |
| IRS Publication 17 brackets (2024) | Finance Act 2024 slabs (FY 2024-25) |
| `$` USD | `₹` INR with Indian grouping (1,23,45,678) |

---

## Tech stack change

| Component | Before | After |
|---|---|---|
| Vector store | ChromaDB (file-based at `backend/chroma_db/`) | **pgvector** extension on PostgreSQL |
| Embedding model | SentenceTransformer all-MiniLM-L6-v2 (via Chroma) | Same model, used directly + stored in pgvector (384-dim) |
| Multi-agent | LangGraph **and** AutoGen (parallel, unintegrated) | **LangGraph only** — AutoGen retired |
| Postgres image | `postgres:18` (no vector extension) | `pgvector/pgvector:pg16` |
| LangGraph checkpointing | `PostgresSaver.from_conn_string` (broken context-mgr API) | `InMemorySaver` (Phase 0); `AsyncPostgresSaver` deferred to Phase 3 |
| Tax math location | LangGraph LLM calls + frontend US brackets + `pdf_generator.py` (3 places) | `tax_engine_in.py` (single deterministic source of truth) |
| Form-data extraction | AutoGen DocumentAgent (LLM-based, unpersisted) | Pydantic `Form16Extractor` (regex-based, persisted to `form16` table) |

---

## Database schema change

Run `python -m scripts.recreate_db --force` from `backend/` to apply.

### Removed tables
- `tax_forms` — US tax return parent record
- `dependents` — US dependents (with `ssn_encrypted`)
- `w2_forms` — US W-2 income
- `form_1099s` — US 1099 forms
- `user_input_data` — generic user-input audit trail (subsumed by `compliance_checks`)

### Added tables
- `form16` — extracted Form 16 (Indian salary TDS certificate)
  - employer_name, employer_tan, employer_pan
  - gross_salary, exempt_allowances, standard_deduction_claimed, professional_tax
  - deductions_80c, deductions_80d, tds_deducted, quarter_wise_tds (JSON)
  - raw_ocr_text, source_document_id, extraction_status
- `itr1_filings` — computed ITR-1 filing
  - regime ('old' | 'new'), assessment_year
  - gross_income, taxable_income, slab_tax, rebate_87a, surcharge, cess, total_tax
  - tds_paid, refund_due, tax_due
  - itr1_json (IT Dept schema), pdf_path
  - status ('draft' | 'computed' | 'finalized')
- `rag_documents` — pgvector-backed rulebook chunks
  - collection (default `itr_rulebook`), source, chunk_index, topic, content
  - embedding `Vector(384)`, extra_metadata (JSON)

### Modified tables
- `users` — added `pan_encrypted`, `aadhaar_encrypted`; relationships now `form16s` and `filings`
- `user_profiles` — added `preferred_regime` ('old' | 'new'), replaced `filing_status_history` (US) with `filing_history`, added `preferred_assessment_year`
- `compliance_checks` — now FKs to `itr1_filings.id` instead of `tax_forms.id`

### Pgvector setup

`backend/scripts/recreate_db.py` runs `CREATE EXTENSION IF NOT EXISTS vector;` before `Base.metadata.create_all`. The Postgres image (`pgvector/pgvector:pg16`) ships with the `vector` extension preinstalled.

---

## Code change summary by directory

### `backend/app/`

| File | Change |
|---|---|
| `main.py` | Lifespan event handler (replaces deprecated `on_event`); `openapi_url=/api/openapi.json` for correct Swagger docs path; root endpoint reads `app.title` / `app.version` instead of hardcoded strings; dropped `tax_forms` / `filing` router includes; mounted `filing_v2` |
| `models.py` | Full rewrite — see Database Schema Change above |
| `schemas.py` | Trimmed to User / UserProfile / Auth / Chat / Health. Pydantic v2 `field_validator` and `model_config` |
| `crud.py` | Trimmed to User / UserProfile / AuditLog / authenticate_user; uses `model_dump(exclude_unset=True)` |
| `agents_v2/state.py` | Added `regime`, `form16_id`, `tax_breakdown`, `itr1_filing_id`, `pdf_path` |
| `agents_v2/nodes.py` | Full rewrite. Interviewer extracts via `EXTRACTION:` JSON marker; researcher queries pgvector; calculator calls `tax_engine_in.compute_filing`; auditor enforces 5 invariants on `TaxBreakdown` |
| `agents_v2/graph.py` | Switched checkpointer from broken `PostgresSaver.from_conn_string` to `InMemorySaver`; removed Unicode emoji prints (Windows cp932 crash) |
| `api/auth.py` | unchanged |
| `api/users.py` | unchanged |
| `api/documents.py` | AutoGen DocumentAgent removed; Form 16 detection + structured extraction + `form16` row write |
| `api/filing_v2.py` | New endpoints: `POST /api/v2/calc/preview`, `POST /api/v2/filing/start` (manual or form16_id), `GET /api/v2/filing/{id}/pdf|json|status`, `POST /api/v2/filing/chat/{start,message}`; emits `filing.*` WS events when `client_id` provided |
| `api/ws.py` | AutoGen handler removed; `/api/ws/{client_id}` registers per-client routes; passes through inbound messages as `event:echo` |
| `api/filing.py` | **Deleted** (W-2 box references) |
| `api/tax_forms.py` | **Deleted** (US tax-form CRUD) |
| `services/tax_engine_in.py` | **New** — deterministic Indian tax engine |
| `services/tax_engine_in_constants.py` | **New** — FY 2024-25 slabs, 87A, surcharge bands, 80C/80D, cess |
| `services/itr1_json_builder.py` | **New** — IT Dept ITR-1 JSON shape |
| `services/pdf_generator.py` | Rewritten for ITR-1 layout with `_rs()` Indian-grouping formatter; old US function kept as `generate_tax_return_pdf` deprecated alias |
| `services/form16_extractor.py` | **New** — regex-based parser with `Form16Data` Pydantic schema and confidence scoring |
| `rag/ingest.py` | **Rewritten** — SentenceTransformer + paragraph chunking + topic auto-tag → `rag_documents` rows (replaces ChromaDB writes) |
| `rag/retriever.py` | **Rewritten** — pgvector `cosine_distance` query with optional `topic_filter`; returns `RetrievedChunk` dataclass with score |
| `sdui/schema.py` | `update_forward_refs()` → `model_rebuild()` (Pydantic v2) |
| `websockets/manager.py` | Per-`client_id` routing via `send_to_client()`; `broadcast()` retained for general announcements |
| `autogen_agents/` | **Entire directory deleted** |

### `backend/scripts/`
- `recreate_db.py` — **new** dev helper. Runs `CREATE EXTENSION IF NOT EXISTS vector` then `drop_all` + `create_all`. `--force` skips the typed confirmation.

### `backend/tests/`
- New: `tests/api/test_filing_v2_phase0.py` (11 tests), `tests/api/test_ws_phase3.py` (3 tests), `tests/integration/test_phase0_e2e.py` (6 tests)
- New: `tests/services/test_tax_engine_in.py` (33 tests), `test_itr1_json_builder.py` (3), `test_pdf_generator.py` (2), `test_form16_extractor.py` (8)
- New: `tests/rag/test_pgvector_rag.py` (4 live integration tests; skip cleanly if Postgres unreachable)
- Existing: `tests/test_metamorphic.py` (5 hypothesis tests, untouched)
- `tests/conftest.py` — uses `StaticPool` so SQLite in-memory is shared across FastAPI dependency-injected sessions
- `pytest.ini` — `asyncio_mode=auto`, suppresses passlib deprecation warnings

### `backend/requirements.txt`
- **Removed**: `pyautogen==0.2.10`
- **Loosened pins** (Python 3.13/3.14 wheels): `psycopg2-binary>=2.9.9`, `pandas>=2.1.4`, `numpy>=1.26.3`, `pydantic>=2.5.3`
- **Added**: `psycopg[binary]>=3.3` (langgraph-checkpoint-postgres dep), `langgraph>=1.0`, `langgraph-checkpoint-postgres>=3.0`, `langchain-openai>=1.0`, `email-validator>=2.0`

### `src/` (frontend)
- `agents/tools/taxCalculationTools.ts` — full rewrite. Thin client over `POST /api/v2/calc/preview`. Tools: `calculate_income_tax`, `compare_regimes`, `taxable_income_after_deductions`, `compare_scenarios`. Removed all hardcoded US brackets and filing statuses. INR formatting via `Intl.NumberFormat('en-IN')`.
- `components-vue/export/TaxReportExporter.vue` — HTML and CSV templates rewritten for ITR-1 (regime, FY 2024-25 slabs, 80C / 80D / 87A). Removed IRS Form 1040, EITC, Child Tax Credit references.
- `components-vue/analysis/RealTimeAnalysis.vue` — `$2,600` → `₹2,60,000`; standard deduction guidance updated to 80C; `toLocaleString('en-IN')`.

### Removed top-level files
- `LLM.txt` (root) — US IRS content for LLMs
- `public/llm-tax-knowledge.txt` — same
- `backend/test_autogen.py` — orphan AutoGen test

---

## Configuration changes

### `.env.dev`
- `OPENAI_API_KEY` is the canonical name (was `VITE_OPENAI_API_KEY` in some places); the LangGraph nodes accept either.

### `docker-compose.yml`
- Postgres image: `pgvector/pgvector:pg16` (was `postgres:18`)
- Other services unchanged

### `.gitignore`
- Added `backend/app/uploads/` (generated PDFs)
- Added `backend/chroma_db/` (legacy ChromaDB persistence — safe to delete from disk)

---

## API surface change

### Before (Phase 0)
- `POST /api/v2/filing/start` — initial chat message via LangGraph
- `POST /api/v2/filing/message` — continue thread
- `GET /api/v2/filing/status/{thread_id}` — get state

### After (Phase 0–4)
- `POST /api/v2/calc/preview` — stateless tax computation
- `POST /api/v2/filing/start` — manual entry **or** `form16_id` → persists `ITR1Filing` + writes PDF
- `GET /api/v2/filing/{id}/pdf` — ITR-1 PDF download
- `GET /api/v2/filing/{id}/json` — ITR-1 JSON (IT Dept schema)
- `GET /api/v2/filing/{id}/status` — filing summary
- `POST /api/v2/filing/chat/start` — start LangGraph chat thread
- `POST /api/v2/filing/chat/message` — continue chat thread

WebSocket `/api/ws/{client_id}` now emits structured `event` payloads:
- `connected` — on accept
- `echo` — for inbound messages (Phase 0 placeholder)
- `filing.starting` / `filing.calculating` / `filing.complete` — when `client_id` is supplied to `/filing/start`

---

## Test summary

Run from `backend/`:

```bash
python -m pytest tests/ -q          # 75 tests, ~40s (incl. live pgvector RAG)
python -m pytest tests/ --ignore=tests/rag -q   # 71 tests, ~6s (sans RAG)
```

| Group | Count |
|---|---|
| Tax engine | 33 |
| Form 16 extractor | 8 |
| ITR-1 JSON builder | 3 |
| PDF generator | 2 |
| Filing API (preview, start manual + form16, downloads, 404 paths) | 11 |
| WebSocket events (connect, echo, filing.complete delivery) | 3 |
| LangGraph integration (calculator, auditor, full pipeline) | 6 |
| pgvector RAG (live; skips if Postgres down) | 4 |
| Hypothesis metamorphic | 5 |
| **Total** | **75** |

---

## Known gaps / out of scope

These were intentionally deferred and are not bugs:

1. **Real IT Dept PDF ingestion** — the RAG corpus is `backend/tax_rules.txt` + scraped content from `incometax.gov.in` (5 chunks). The full Income Tax Act 1961, ITR-1 instructions (AY 2025-26), Finance Act 2024, and CBDT circulars on 80C/80D have not been fetched.
2. **E-filing submission** — no integration with incometax.gov.in. The system produces ITR-1 JSON in IT Dept schema shape but does not submit it.
3. **AsyncPostgresSaver** — LangGraph currently uses `InMemorySaver` so threads do not survive restart. Switching to async Postgres persistence is Phase 3+.
4. **Frontend tool modules** — `complianceTools.ts`, `advisoryTools.ts`, `documentProcessingTools.ts` still contain US tax thresholds. They aren't on the data-pipeline path (the actual pipeline goes through `taxCalculationTools.ts` → backend), but a future cleanup should rewrite them or delete unused tools.
5. **Form 16 extractor** is regex-based. Low-confidence extractions return `extraction_status: "review_required"` so the user can correct fields. A future revision could fall back to GPT-4 with function calling for ambiguous documents.
6. **RBAC** — `/api/users/...` admin checks are TODOs. Currently any authenticated user can list users.

---

## Session 2 changes — 2026-05-09

### Bug fixes

#### `backend/main.py`
- **Broken imports**: `tax_forms` and `filing` modules were still referenced but deleted in Session 1. Fixed by removing them and keeping only `filing_v2`.
- **CORS ports**: Vite dev server can bind to ports 8081–8083 when lower ports are busy. Added `http://localhost:8081`, `http://localhost:8082`, `http://localhost:8083`, and `http://127.0.0.1:8083` to `allow_origins`.

#### `src/pages/WizardFiling.vue`
- **Submit button stuck disabled**: The disabled condition was hardcoded as `currentStep === 3 && previewLoading`. For forms with more than 4 steps the review step is not step 3. Changed to `stepKey === 'review' && previewLoading` where `stepKey` is computed from the current step's `name` field.
- **Review page not scrollable**: Nested flex layout was missing `overflow-hidden min-h-0` on the left panel div and the Card. Without `min-h-0`, CSS `min-height: auto` lets flex children grow past parent bounds, defeating `overflow-y-auto`. Fix: added `overflow-hidden min-h-0` to the column div and Card.

#### `src/pages/Chat.vue`
- **Chat message area not scrollable**: Same root cause as WizardFiling. Fix:
  - Left column div: added `overflow-hidden min-h-0`
  - Header div: added `flex-shrink-0` so it never compresses
  - Card: added `min-h-0`
  - Input footer: added `flex-shrink-0`

### RAG improvements — `backend/app/rag/ingest.py`

Scraped web content includes metadata headers in the format:
```
[SOURCE: https://...] [SCRAPED: 2026-05-08] [FY: 2024-25]
```
These headers were being embedded as part of chunk text, polluting vector similarity. Fixed by:
- Adding `_SCRAPED_HEADER_RE` compiled regex to detect the header pattern.
- Adding `_strip_scraped_header(chunk)` which returns `(cleaned_content, source_url | None)`.
- Updating the `ingest_text` loop to embed `cleaned_content`, store the scraped URL in `extra_metadata["source_url"]` and in the `source` column.

Re-ingested the full corpus after the fix — 62 chunks total (57 from `tax_rules.txt` + 5 scraped chunks from `incometax.gov.in`).

### Database

Sample credentials for local development (created 2026-05-09):

| Field | Value |
|---|---|
| Email | `demo@taxfiler.in` |
| Password | `Test@1234` |
| Role | `filer` |

To reset and recreate run from `backend/`:
```sql
DELETE FROM itr1_filings;
DELETE FROM form16;
DELETE FROM audit_logs;
DELETE FROM user_profiles;
DELETE FROM users;
```
Then re-create the user via `/api/auth/register` or directly with `get_password_hash` from `passlib`.
