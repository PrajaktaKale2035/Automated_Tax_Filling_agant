# Backend Development Status

> **Updated 2026-05-09.** For the full US-to-India migration changelog see [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md).

---

## Current Status — Phase 0–8 complete (Indian ITR-1)

**Date:** 2026-05-09
**Branch:** `develop`
**Status:** 88/88 tests pass, 0 warnings.

---

### What works end-to-end

- Deterministic Indian tax engine (`backend/app/services/tax_engine_in.py`) — FY 2024-25 slabs, senior (60+) and super-senior (80+) citizen basic exemptions, standard deduction ₹75K/₹50K, 80C/80D, rebate 87A, surcharge, 4% cess
- Indian ITR-1 schema in Postgres — 7 tables + `UserRole` enum (`filer / helper / read_only`)
- Role-based access control via `require_role()` dependency in `api/deps.py`
- **XAI engine** (`services/xai_engine.py`) — `explain_breakdown()`, `what_if()`, `compare_regimes()`; exposed on `/api/v2/explain/*`
- **Adaptive engine** (`services/adaptive_engine.py`) — EMA-weighted cognitive load from error rate / typing speed / help clicks; mode suggestion thresholds; exposed on `POST /api/users/behavior`
- **pgvector** RAG over the curated FY 2024-25 rulebook — 29 sections (~57 chunks); pre-warmed at startup
- LangGraph workflow: `interviewer → researcher → calculator → auditor`; threads persisted to Postgres via `AsyncPostgresSaver` (survives restart)
- Multi-provider LLM in `nodes.py`: Gemini / OpenAI / Ollama — switch via `LLM_PROVIDER` in `.env`
- Form 16 OCR upload + structured extraction → `form16` table
- ITR-1 JSON in IT Dept schema + ITR-1 PDF (INR Indian grouping)
- WebSocket `filing.starting / .calculating / .complete` events keyed to `client_id`
- Web scraper (`scripts/scraper.py`) — fetches and chunks `incometax.gov.in` pages and PDFs for RAG ingestion
- 25 metamorphic invariants in `tests/test_metamorphic.py` (monotonicity, non-negativity, cess composition, surcharge bands, regime rationality, etc.)

---

### API routes

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/auth/register` | — | |
| POST | `/api/auth/login` | — | form-urlencoded |
| GET | `/api/auth/me` | Bearer | |
| POST | `/api/auth/logout` | Bearer | |
| GET | `/api/users/me` | Bearer | |
| PUT | `/api/users/me` | Bearer | |
| GET | `/api/users/me/profile` | Bearer | |
| PUT | `/api/users/me/profile` | Bearer | |
| POST | `/api/users/behavior` | Bearer | adaptive engine input |
| POST | `/api/documents/upload` | Bearer | OCR + Form 16 extraction |
| POST | `/api/v2/calc/preview` | Bearer | stateless tax computation |
| POST | `/api/v2/filing/start` | Bearer + filer/helper role | persist ITR1Filing |
| GET | `/api/v2/filing/{id}/pdf` | Bearer | |
| GET | `/api/v2/filing/{id}/json` | Bearer | IT Dept ITR-1 JSON |
| GET | `/api/v2/filing/{id}/status` | Bearer | |
| POST | `/api/v2/filing/chat/start` | Bearer | LangGraph chat |
| POST | `/api/v2/filing/chat/message` | Bearer | continue thread |
| POST | `/api/v2/explain/` | Bearer | XAI line explanations |
| POST | `/api/v2/explain/whatif` | Bearer | what-if counterfactual |
| POST | `/api/v2/explain/regime-compare` | Bearer | old vs new comparison |
| WS | `/api/ws/{client_id}` | — | realtime filing events |
| GET | `/api/sdui/dashboard/{user_id}` | Bearer | adaptive UI schema |

---

### Test breakdown

| File | Tests | Covers |
|------|-------|--------|
| `tests/test_tax_engine.py` | 13 | Senior/super-senior citizen slab edge cases, age_category |
| `tests/services/test_tax_engine_in.py` | 33 | Core tax engine functions (slabs, deductions, rebate, surcharge, cess) |
| `tests/test_xai_engine.py` | 5 | XAI engine: explain_breakdown, what_if, compare_regimes |
| `tests/test_adaptive_engine.py` | 7 | Cognitive load scoring, mode suggestion thresholds |
| `tests/test_metamorphic.py` | 25 | Property-based invariants (monotonicity, composition, regime rules) |
| `tests/scripts/test_scraper.py` | 5 | Scraper utilities (chunking, dedup, header format, HTML parsing) |
| **Total** | **88** | 0 warnings |

---

### Known gaps (intentional, deferred)

- Live scraping of `incometax.gov.in` works (`scripts/scraper.py`). Run `python -m scripts.scraper --fy 2024-25` to refresh. CBDT.gov.in DNS is intermittently unreachable; warnings are logged and execution continues.
- Full PDF ingestion of Income Tax Act / Finance Act notices — currently uses curated `tax_rules.txt` plus scraped HTML chunks.
- E-filing submission to incometax.gov.in
- Frontend tool modules outside the data pipeline (`complianceTools.ts`, `advisoryTools.ts`) still contain US thresholds — not on the `tax_engine_in` path
- Full integration tests for XAI and adaptive engine endpoints (unit tests pass; API-level integration tests pending)
