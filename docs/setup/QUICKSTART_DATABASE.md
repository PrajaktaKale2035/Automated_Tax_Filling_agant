# Quick Start — Database & Schema

This project uses **PostgreSQL 16 with the pgvector extension** for both relational data and embeddings.

---

## Method 1 — Docker (recommended)

The compose file pins the `pgvector/pgvector:pg16` image, so the `vector` extension is available out of the box.

```bash
docker-compose up -d postgres
```

That's it. Skip to [Initialize the schema](#initialize-the-schema).

---

## Method 2 — Local PostgreSQL install

If you prefer a native install (Windows or macOS/Linux), you also need pgvector available.

### 2a. Install Postgres 16+

**Windows automated**: double-click `setup-postgresql.bat` (or run `setup-postgresql.ps1` as Administrator). The script:
- Checks for an existing install
- Walks you through download / Chocolatey install if missing
- Creates the `tax_filing_db` database and `taxagent` user
- Tests the connection

**Manual**: download from [enterprisedb.com/downloads/postgres-postgresql-downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads). Use these settings:
- Password: `taxagent_secure_password_2024`
- Port: `5432`
- Components: PostgreSQL Server, pgAdmin 4, Command Line Tools

### 2b. Install pgvector

```bash
# Connect to your DB
psql -U postgres -d tax_filing_db

CREATE EXTENSION IF NOT EXISTS vector;
\q
```

If `CREATE EXTENSION` fails, you need to install pgvector itself:
- **Windows**: download a prebuilt binary from [github.com/pgvector/pgvector/releases](https://github.com/pgvector/pgvector/releases) and copy the `.dll` to `C:\Program Files\PostgreSQL\16\lib\`, the `.control` and `.sql` files to `C:\Program Files\PostgreSQL\16\share\extension\`. Restart the Postgres service. Then retry `CREATE EXTENSION vector`.
- **macOS / Linux**: `brew install pgvector` or follow the [pgvector README](https://github.com/pgvector/pgvector#installation).

---

## Initialize the schema

`recreate_db.py` is a dev helper that:
1. Runs `CREATE EXTENSION IF NOT EXISTS vector` (idempotent)
2. Drops every table in the SQLAlchemy metadata
3. Recreates them from the current `models.py`

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate                # Windows
# source venv/bin/activate              # macOS / Linux

pip install -r requirements.txt

# DESTRUCTIVE: drops all data and recreates the schema.
# Omit --force to be prompted for typed "yes" confirmation.
python -m scripts.recreate_db --force
```

Expected output:

```
Ensuring pgvector extension...
Dropping all tables...
Creating all tables from current models...
Done.
Tables now defined:
  - audit_logs
  - compliance_checks
  - form16
  - itr1_filings
  - rag_documents
  - user_profiles
  - users
```

---

## Ingest the Indian tax rulebook

The pgvector `rag_documents` table is populated from the curated `backend/tax_rules.txt`:

```bash
cd backend
python -m app.rag.ingest
# -> Ingested 7 chunks from tax_rules.txt into 'itr_rulebook'.
```

Verify retrieval:

```bash
python -m app.rag.retriever
# -> top-3 chunks for "Surcharge for 1 crore income" with cosine scores.
```

A future ingestion run can add real IT Department PDFs (Income Tax Act 1961, ITR-1 instructions, Finance Act 2024, CBDT circulars). Use `app.rag.ingest.ingest_directory(path)` to process a folder.

---

## Database credentials

```
Host:     localhost
Port:     5432
Database: tax_filing_db
Username: taxagent
Password: taxagent_secure_password_2024
```

These come from `docker-compose.yml` and `backend/.env.dev`. Override per-environment with the `DATABASE_URL` env variable (read by `app/database.py`).

---

## Schema overview

7 tables, all India-aligned (ITR-1):

| Table | Purpose |
|---|---|
| `users` | User account + encrypted PAN/Aadhaar |
| `user_profiles` | Adaptive UI prefs, regime preference, filing history |
| `form16` | Extracted Form 16 records (one per uploaded document) |
| `itr1_filings` | Computed ITR-1 filings with `itr1_json` and `pdf_path` |
| `compliance_checks` | Per-filing audit results |
| `audit_logs` | User action history |
| `rag_documents` | Vector embeddings of the IT rulebook (pgvector) |

See [`docs/PROJECT_STRUCTURE.md`](../PROJECT_STRUCTURE.md) for the full ERD and column list, or read `backend/app/models.py` directly.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'psycopg2'` during pytest
The pinned `psycopg2-binary==2.9.9` lacks Python 3.13/3.14 wheels. Newer pip pulls the latest unpinned. The current `requirements.txt` uses `>=2.9.9` to allow this.

### `extension "vector" is not available`
You're hitting Method 2 territory — pgvector isn't installed system-wide. Use the Docker image (Method 1) or install pgvector following the link above.

### `no such table: users` in pytest
Confirms the test fixture isn't sharing the in-memory SQLite database across connections. The `tests/conftest.py` fixture uses `StaticPool` to fix this — make sure you're on the latest revision.

### Connection refused on `localhost:5432`
Postgres isn't running.
- Docker: `docker-compose ps` to check; `docker-compose up -d postgres`
- Native: `Get-Service postgresql*` (Windows) or `brew services list` (macOS) — start the service.

### Stale ChromaDB directory
The project no longer uses ChromaDB. If `backend/chroma_db/` exists from an older checkout, delete it; it's also gitignored.

---

## Next steps

1. Configure `OPENAI_API_KEY` in `backend/.env.dev` (only required for the LangGraph chat flow)
2. Start the API: `python -m uvicorn app.main:app --reload`
3. Open `http://localhost:8000/api/docs` to explore the endpoints
4. Smoke test: `curl -X POST http://localhost:8000/api/v2/calc/preview -H "Content-Type: application/json" -d '{"gross_income":600000,"deductions":{},"regime":"new","is_salary_income":true}'`
