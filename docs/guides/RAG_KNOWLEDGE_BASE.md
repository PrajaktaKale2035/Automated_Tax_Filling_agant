# Extending the ITR Rulebook RAG Knowledge Base

How to add, replace, and verify content in the pgvector-backed Indian tax rulebook
that grounds the LangGraph agent.

---

## How the rulebook works

| Piece | Value |
|---|---|
| Source file | `backend/tax_rules.txt` (29 sections, FY 2024-25 / AY 2025-26) |
| Storage table | `rag_documents` (PostgreSQL + pgvector extension) |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384 dim) |
| Similarity | Cosine distance via pgvector `<=>` operator |
| Default collection | `itr_rulebook` |
| Ingest CLI | `python -m app.rag.ingest` |
| Retriever | `backend/app/rag/retriever.py` (LangChain `BaseRetriever`) |

A **collection** is a logical namespace inside `rag_documents` (column: `collection`).
Multiple collections coexist in the same table; the retriever queries one at a time.
The default agent only reads `itr_rulebook` — use a separate collection name if you
want to add a knowledge base that should not be mixed in (e.g. GST rules).

Ingest writes one row per chunk with: `collection`, `source` (filename),
`chunk_index`, `topic` (auto-detected, see below), `content`, and the 384-dim
`embedding`. Query embeddings are L2-normalised, so cosine distance is in `[0, 2]`
and the retriever maps it to a similarity score in `[0, 1]` (higher is better).

---

## Formatting content for ingestion

The chunker splits on **blank lines** (`\n\s*\n`). One section = one paragraph
separated by an empty line. Keep each chunk self-contained — the retriever returns
one chunk at a time, so context that lives in a different paragraph will be lost.

Good:

```
12. Section 80EE - First-Time Home Buyer Interest Deduction (Old Regime Only):
   Additional Rs 50,000 deduction on home loan interest, over and above 24(b).
   Conditions: loan sanctioned between 1-Apr-2016 and 31-Mar-2017, loan amount
   <= Rs 35 lakh, property value <= Rs 50 lakh, no other house owned at sanction.

13. Next section header...
```

Bad — single block, no blank line, will become one giant chunk:

```
12. Section 80EE...
13. Next section...
```

Aim for ~500-1500 characters per chunk. Very long chunks dilute embedding
relevance; very short chunks lack context.

---

## CLI reference

All commands run from `backend/` with the venv activated.

```bash
# Default: ingests tax_rules.txt, REPLACES the itr_rulebook collection
python -m app.rag.ingest

# Show every chunk currently in the collection (source / topic / index)
python -m app.rag.ingest --list

# Replace the collection with a different .txt file
python -m app.rag.ingest --file path/to/cbdt_circular.txt

# APPEND a file without wiping existing chunks
python -m app.rag.ingest --file extra_rules.txt --append

# Ingest every *.txt inside a directory (replaces collection on first file)
python -m app.rag.ingest --dir extra_rules/ --pattern "*.txt"

# Append a directory of markdown files into an existing collection
python -m app.rag.ingest --dir notes/ --pattern "*.md" --append

# Ingest a text-based PDF (requires: pip install pypdf)
python -m app.rag.ingest --pdf income_tax_act_chapter_vi_a.pdf --append

# Use a separate collection - does NOT touch itr_rulebook
python -m app.rag.ingest --file gst_rules.txt --collection gst_kb

# Inspect a non-default collection
python -m app.rag.ingest --list --collection gst_kb
```

Flag summary:

| Flag | Effect |
|---|---|
| `--file PATH` | Single text file. Mutually exclusive with `--dir` / `--pdf` / `--list`. |
| `--dir PATH` | Every file matching `--pattern` in the directory. |
| `--pdf PATH` | Text-based PDF via `pypdf`. See caveat below. |
| `--list` | Print stored chunks for `--collection` and exit. |
| `--collection NAME` | Read/write target (default `itr_rulebook`). |
| `--pattern GLOB` | Used with `--dir` (default `*.txt`). |
| `--append` | Add chunks instead of replacing the collection. |

Without `--append`, every ingest **wipes the target collection first**. This is
the right default when re-running after editing `tax_rules.txt`; it is the wrong
default when adding a supplemental file.

---

## PDF caveat

`--pdf` uses `pypdf.PdfReader.extract_text()`. It works only on PDFs with
**selectable text** (digital PDFs from CBDT, the Income Tax Act, the Finance
Act, etc.). Scanned image PDFs — Form 16 photocopies, screenshot exports —
extract to empty strings; the CLI will exit with a warning.

For scanned user documents, do **not** route them through this CLI. Use:

```bash
curl -F "file=@form16.pdf" -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/documents/upload
```

That endpoint runs Tesseract OCR and writes parsed fields to the `form16` table —
not to RAG. See "What NOT to put in the rulebook" below.

---

## Adding new topic keywords

When a chunk is ingested, `_infer_topic()` in `backend/app/rag/ingest.py` scans
the lower-cased text for keywords and assigns a `topic` label. The retriever
can then filter by topic (`topic_filter` arg, `?topic=` query param).

Two tiers, defined as ordered lists at the top of `ingest.py`:

- `_SPECIFIC_KEYWORDS` — always wins over generic. Within the tier, the keyword
  with the most word-boundary matches wins; ties broken by list order
  (earlier = higher priority).
- `_GENERIC_KEYWORDS` — fallback only when no specific keyword matches.

Matching is `\b<needle>\b` (word boundaries), so `cess` will not match inside
`excess`. Order matters: list more specific terms before broader ones.

Current mappings (read `ingest.py` for the source of truth):

| Topic | Triggers (keywords) |
|---|---|
| `cess` | cess, health and education |
| `marginal-relief` | marginal relief |
| `rebate-87a` | 87a, rebate |
| `surcharge` | surcharge |
| `80C` | 80c |
| `80CCD` | 80ccd, nps, national pension |
| `80D` | 80d |
| `80G` | 80g, donation |
| `80TTA` | 80tta, 80ttb |
| `lta` | lta, leave travel |
| `professional-tax` | professional tax |
| `gratuity` | gratuity, leave encashment |
| `hra` | hra, house rent |
| `house-property` | house property, 24b, self-occupied |
| `senior-citizen` | super senior, senior citizen |
| `regime-comparison` | break-even, when to choose |
| `new-regime-exclusions` | 115bac, disallowed |
| `form-16` | form 16 |
| `tds` | tds |
| `standard-deduction` | standard deduction |
| `ais-26as` | 26as, annual information |
| `identity` | pan, aadhaar |
| `deadline` | 234f, july 31, belated |
| `advance-tax` | advance tax, 234b, 234c |
| `e-verification` | e-verification, itr-v |
| `budget-2024` | budget 2024, finance act 2024 |
| `itr1-eligibility` | itr-1, sahaj |
| `slabs` (generic) | regime, slab |

When adding new content with new domain language, edit
`backend/app/rag/ingest.py`, append a `("needle", "topic")` tuple to
`_SPECIFIC_KEYWORDS`, and re-ingest. Place more-specific phrases earlier in the
list when ties matter.

---

## Verifying retrieval after ingest

Quick health check:

```bash
python -m app.rag.ingest --list
```

Direct similarity search via the API:

```bash
curl -s "http://localhost:8000/api/v2/rag/search?q=section+80EE+home+loan&k=3" \
  | python -m json.tool
```

Filter by topic:

```bash
curl -s "http://localhost:8000/api/v2/rag/search?q=rebate&k=3&topic=rebate-87a" \
  | python -m json.tool
```

Run the retriever module directly (no server needed):

```bash
python -m app.rag.retriever
```

That prints top-3 hits for four canned queries plus a LangChain-retriever round
trip. Useful for sanity-checking that a new chunk is reachable. Scores below
~0.35 usually mean the query and chunk vocabulary are not aligned — rephrase
the chunk or add a synonym sentence.

---

## What NOT to put in the rulebook

The `rag_documents` table is **shared across all users** and has no `user_id`
column. It must contain only generic ITR rules and government guidance.

Do not ingest:

- Form 16 contents (employer name, gross salary, TDS amounts, PAN of employee).
  These live in the `form16` table per user, populated by
  `POST /api/documents/upload` after Tesseract OCR.
- AIS / 26AS extracts for a specific taxpayer.
- Any PII — names, PANs, Aadhaar numbers, bank accounts.
- Filed ITR JSON / past returns.

User-specific data flows through `form16` and `filings` tables, never through
the RAG pipeline. Mixing them would leak one user's data into another user's
agent context.

---

## Worked example: adding Section 80EE

1. **Append the section to `backend/tax_rules.txt`**, separated by a blank line:

   ```
   29. Section 80EE - First-Time Home Buyer Interest Deduction (Old Regime Only):
      Additional Rs 50,000 deduction on home-loan interest, over and above the
      Rs 2,00,000 limit under Section 24(b). Conditions: loan sanctioned between
      1-Apr-2016 and 31-Mar-2017, loan amount <= Rs 35 lakh, property value <=
      Rs 50 lakh, taxpayer owns no other residential house at sanction date.
      Not available under the new regime.
   ```

2. **(Optional) add a topic keyword** in `backend/app/rag/ingest.py` so the
   chunk filters cleanly. Edit `_SPECIFIC_KEYWORDS` and append:

   ```python
   ("80ee",                 "80EE"),
   ("first-time home",      "80EE"),
   ```

3. **Re-ingest** and verify:

   ```bash
   cd backend
   python -m app.rag.ingest                      # replaces itr_rulebook
   python -m app.rag.ingest --list | grep 80EE   # confirm chunk + topic
   curl -s "http://localhost:8000/api/v2/rag/search?q=first+time+home+buyer&k=3" \
     | python -m json.tool
   ```

   The new chunk should appear with `topic: "80EE"` and a similarity score
   above ~0.5 for the query above.
