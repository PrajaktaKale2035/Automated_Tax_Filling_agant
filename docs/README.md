# Documentation Index — Indian Tax Filing AI Agent

This is the documentation hub for the Indian ITR-1 (Sahaj) tax filing system,
FY 2024-25 / AY 2025-26.

> **First time on the project?** Read [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) —
> it explains the US-to-India migration so older PRs and historical commit
> messages remain readable.

---

## Layout

```
docs/
├── README.md               # This index
├── MIGRATION_NOTES.md      # US -> India changelog (read first if catching up)
├── PROJECT_STRUCTURE.md    # Directory layout and table schema
├── BACKEND_STATUS.md       # Phase status snapshot
├── setup/                  # Database setup
├── guides/                 # Developer how-tos
├── api/                    # REST API reference
└── superpowers/            # Design specs, audits, plans (history)
```

---

## Setup and installation

Start at the project root and follow these in order:

1. **[`PHASE1_SETUP.md`](../PHASE1_SETUP.md)** — full setup guide for a fresh
   machine. Covers Docker, venv, `.env` template, all three LLM providers
   (Ollama / Gemini / OpenAI), first-time DB init, smoke tests, troubleshooting.
2. **[`setup/QUICKSTART_DATABASE.md`](setup/QUICKSTART_DATABASE.md)** —
   Postgres + pgvector (Docker or local install).
3. **[`setup/POSTGRESQL_INSTALLATION_WINDOWS.md`](setup/POSTGRESQL_INSTALLATION_WINDOWS.md)** —
   Windows-specific notes when not using Docker.
4. **[`setup/POSTGRESQL_SETUP.md`](setup/POSTGRESQL_SETUP.md)** —
   manual Postgres configuration.

---

## Developer guides

| Guide | When to read |
|---|---|
| [`guides/RAG_KNOWLEDGE_BASE.md`](guides/RAG_KNOWLEDGE_BASE.md) | Adding new content (text or PDF) to the ITR rulebook RAG |
| [`guides/UPDATING_FOR_NEW_FY.md`](guides/UPDATING_FOR_NEW_FY.md) | When the Union Budget changes slabs / deductions for the next FY |

---

## API reference

| Doc | Covers |
|---|---|
| [`api/API_REFERENCE.md`](api/API_REFERENCE.md) | All REST endpoints, request/response schemas |
| [`api/AUTHENTICATION.md`](api/AUTHENTICATION.md) | JWT login flow, Bearer-token usage, protected vs public endpoints |

Live OpenAPI when the backend is running:
- Swagger UI: <http://localhost:8000/api/docs>
- OpenAPI JSON: <http://localhost:8000/api/openapi.json>

---

## Architecture and history

| Doc | Purpose |
|---|---|
| [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) | What changed in the US-to-India migration |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | File and directory map, DB tables |
| [`BACKEND_STATUS.md`](BACKEND_STATUS.md) | Current backend status, what works end-to-end |
| [`superpowers/`](superpowers/) | Original design specs, broken-pipelines audit, Phase 0 plan |

---

## Quick navigation by task

| I want to... | Start here |
|---|---|
| Set up the project on a fresh machine | [`PHASE1_SETUP.md`](../PHASE1_SETUP.md) |
| Add a new tax rulebook section | [`guides/RAG_KNOWLEDGE_BASE.md`](guides/RAG_KNOWLEDGE_BASE.md) |
| Update for FY 2025-26 (next year's budget) | [`guides/UPDATING_FOR_NEW_FY.md`](guides/UPDATING_FOR_NEW_FY.md) |
| Authenticate against the API | [`api/AUTHENTICATION.md`](api/AUTHENTICATION.md) |
| Read the request/response shape of any endpoint | [`api/API_REFERENCE.md`](api/API_REFERENCE.md) |
| Understand the LangGraph workflow | [`../walkthrough.md`](../walkthrough.md) |
| Switch LLM providers (Ollama / Gemini / OpenAI) | [`PHASE1_SETUP.md`](../PHASE1_SETUP.md) — "LLM provider selection logic" |

---

## Out of scope (deferred)

- Real IT Department PDF ingestion (Income Tax Act, ITR-1 instructions, Finance Act)
  — currently uses the curated `backend/tax_rules.txt` (29 sections).
- E-filing submission to incometax.gov.in.
- `AsyncPostgresSaver` for LangGraph checkpointing — currently `InMemorySaver`.
