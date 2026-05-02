# Updating the System for a New Financial Year

How to migrate the ITR-1 stack from one Financial Year (FY) to the next, e.g.
FY 2024-25 (AY 2025-26) -> FY 2025-26 (AY 2026-27).

FY = April 1 to March 31. AY (Assessment Year) = FY + 1. Filings in AY 2026-27
report income earned during FY 2025-26.

---

## What changes every year

| Event | Typical date | What it affects |
|---|---|---|
| Union Budget | February 1 | Slabs, standard deduction, 87A rebate, surcharge bands, deduction caps |
| Finance Act passed | late March / early April | Becomes statute; constants are final |
| CBDT notifies ITR forms | April - May | Schema fields, JSON shape, PDF layout |
| New FY starts | April 1 | Apply new constants from this date forward |
| Filing due date | July 31 of AY | Deadline for non-audit individuals |

Wait until the Finance Act is passed (not just the Budget speech) before
hard-coding values - speech proposals occasionally get amended in Parliament.

---

## Files to update (in order)

### a) `backend/app/services/tax_engine_in_constants.py`

Single source of truth for all tax math. Add new FY-suffixed constants
alongside the existing ones; do not delete the old ones (they are needed for
back-filings and tests against historical years). Then extend `SUPPORTED_FYS`.

Constants currently defined for FY 2024-25 (each must be reviewed):

| Constant | FY 2024-25 value | Source |
|---|---|---|
| `NEW_REGIME_SLABS_FY_2024_25` | 0/3L/7L/10L/12L/15L at 0/5/10/15/20/30 % | Sec 115BAC, Finance Act 2024 |
| `OLD_REGIME_SLABS_FY_2024_25` | 0/2.5L/5L/10L at 0/5/20/30 % | unchanged from FY 2023-24 |
| `STANDARD_DEDUCTION_NEW_FY_2024_25` | `75_000` | Sec 16(ia), raised in Budget 2024 |
| `STANDARD_DEDUCTION_OLD_FY_2024_25` | `50_000` | Sec 16(ia) |
| `REBATE_87A_NEW_FY_2024_25` | `{"income_threshold": 700_000, "max_rebate": 25_000}` | Sec 87A new regime |
| `REBATE_87A_OLD_FY_2024_25` | `{"income_threshold": 500_000, "max_rebate": 12_500}` | Sec 87A old regime |
| `CESS_RATE` | `0.04` | Health & Education Cess - rarely changes |
| `SURCHARGE_BANDS_FY_2024_25` | 50L/1Cr/2Cr/5Cr at 10/15/25/37 % | Old regime - 4 bands |
| `SURCHARGE_BANDS_NEW_FY_2024_25` | 50L/1Cr/2Cr at 10/15/25 % | New regime - capped at 25 % |
| `LIMIT_80C` | `150_000` | Sec 80C cap |
| `LIMIT_80D_SELF_BELOW_60` | `25_000` | Sec 80D self/family below 60 |
| `LIMIT_80D_SELF_60_PLUS` | `50_000` | Sec 80D self/family 60+ |
| `SUPPORTED_FYS` | `("2024-25",)` | Tuple of accepted FY strings |

Required edits for the new FY (example: FY 2025-26):

1. Duplicate every `*_FY_2024_25` constant as `*_FY_2025_26` and edit values
   per the new Finance Act.
2. Update `SUPPORTED_FYS = ("2024-25", "2025-26")`.
3. Update `tax_engine_in.py` so the FY-dispatch helpers (`_slabs_for`,
   `apply_deductions`, `apply_rebate_87a`, `compute_surcharge`) pick the right
   constants based on the `fy` argument. Today they hard-reference
   `*_FY_2024_25`; convert to a lookup keyed on `fy`.
4. Change the default in every function signature from `fy: str = "2024-25"`
   to the new current FY.

Deduction caps (`LIMIT_80C`, `LIMIT_80D_*`) currently lack an FY suffix because
they have not changed in years. If the Finance Act revises them, add suffixed
versions and route the lookup through `fy` like the other constants.

### b) `backend/tax_rules.txt`

The 29-section rulebook is the RAG ground truth. The header line and the
following sections must be updated whenever their underlying numbers change:

| Section | Title | When to update |
|---|---|---|
| Header line 1 | "Tax Rules for FY 2024-25 (AY 2025-26)..." | Always |
| 1 | Income Tax Slabs (New Regime) | If new-regime slabs change |
| 2 | Income Tax Slabs (Old Regime) | If old-regime slabs change |
| 3 | Standard Deduction | If either standard deduction amount changes |
| 4 | Section 80C | If `LIMIT_80C` changes |
| 5 | Section 80D | If `LIMIT_80D_*` change |
| 6 | Section 87A Rebate | If thresholds or max rebate change |
| 7 | Surcharge on Income Tax | If surcharge bands change |
| 8 | Health and Education Cess | Only if `CESS_RATE` changes (rare) |
| 16 | Filing Deadline | Always - update July 31 / Dec 31 dates to new AY |
| 17 | Advance Tax | Update due dates to new FY (Jun 15 / Sep 15 / Dec 15 / Mar 15) |
| 18 | 80CCD(1B) | If NPS additional limit changes |
| 23 | Senior Citizen Slabs | If old-regime senior thresholds change |
| 24 | 87A Marginal Relief | Rework break-even example numbers |
| 29 | Budget 20YY Key Changes | Replace with the new Budget summary |

Search-and-replace `2024-25` -> `2025-26` and `AY 2025-26` -> `AY 2026-27`
throughout, then audit each numeric value section by section.

### c) Tests

`backend/tests/services/test_tax_engine_in.py` has hard-coded expected values
that depend on the FY 2024-25 constants. Every parametrized case and assertion
must be recomputed if any slab / cap / rebate moves. Specific landmarks:

- `test_compute_slab_tax` parametrize block - expected slab tax per income.
- `test_apply_deductions_*` - assumes 75k new / 50k old standard deduction.
- `test_rebate_*` - assumes 700k new / 500k old thresholds.
- `test_compute_surcharge` parametrize block - assumes current bands.
- `test_compute_filing_new_regime_low_income_full_rebate` - taxable 525_000 / slab 11_250.
- `test_compute_filing_old_regime_with_80c` - `total_tax = 132_600` for gross 12L + 80C 1L.
- `test_compute_filing_high_income_with_surcharge` - `total_tax = 1_678_820` for gross 60L.

If you keep the old constants alongside the new ones, leave the existing tests
passing under `fy="2024-25"` and add a parallel set under the new FY rather
than rewriting in place. This protects historical math.

`backend/tests/test_metamorphic.py` is property-based and survives slab
changes for free, but verify the `MockEngine` fallback still returns sane
values (it hard-codes a 300k threshold). The full suite must remain at
`75 passed`.

### d) `backend/app/api/filing_v2.py`

Update the default in `FilingStartRequest`:

```python
assessment_year: str = "2025-26"  # FY 2024-25
# -> bump to "2026-27" for FY 2025-26
```

Also bump `CalcPreviewRequest.fy` default from `"2024-25"` to the new FY.

The `ChatStartRequest.initial_message` default mentions `AY 2025-26` - update
the literal string.

---

## Files to update conditionally

Only touch these when the listed thing actually changes.

### PDF templates - if the ITR-1 form layout changes

CBDT typically tweaks the form schema each AY. If the official ITR-1 PDF
layout changes:

- `backend/app/services/pdf_generator.py` - field positions, labels, AY box.
- `backend/app/services/itr1_json_builder.py` - JSON keys and shape if the
  IT Department schema version changes.

Verify against the latest Schema XSD and template PDF published on
`incometax.gov.in -> Downloads -> Income Tax Forms`.

### LangGraph prompts - if regime defaults or interview script change

`backend/app/agents_v2/nodes.py` `_INTERVIEWER_SYSTEM_PROMPT` (line ~99) names
the current AY and any "default regime" guidance. Update the literal text if
the default regime flips or the AY needs to roll forward.

---

## Re-ingest the rulebook

After editing `backend/tax_rules.txt`, refresh the pgvector embeddings:

```bash
cd backend
.\venv\Scripts\activate              # Windows; or: source venv/bin/activate
python -m app.rag.ingest
# Expected: "Ingested 2N chunk(s) from 'tax_rules.txt' into 'itr_rulebook'."

python -m app.rag.ingest --list      # confirm the new content is searchable
```

`ingest` replaces the `itr_rulebook` collection by default - no need to wipe
manually. If you maintain extra appended sources, re-run those `--append`
commands after the base re-ingest.

---

## Run the full test suite

```bash
cd backend
python -m pytest tests/ -q
# Expected: 75 passed (or higher if you added new FY parametrize cases)
```

If `test_metamorphic.py` warns about a missing Rust engine, that is expected
and unrelated to the FY migration.

---

## Sanity smoke test

With backend running (`python -m uvicorn app.main:app --reload`), hit the
stateless preview endpoint with a known income and confirm the new constants
are live:

```bash
# FY 2024-25 baseline: gross 12L + 80C 1L old regime -> total_tax 132_600
curl -s -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":1200000,"deductions":{"80c":100000},"regime":"old","is_salary_income":true,"fy":"2024-25"}' \
  | python -m json.tool
# Expect: "total_tax": 132600

# After migration, target the new FY explicitly
curl -s -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":1200000,"deductions":{"80c":100000},"regime":"old","is_salary_income":true,"fy":"2025-26"}' \
  | python -m json.tool
# Expect: total_tax matching the value you computed by hand from the new slabs
```

Also spot-check the new-regime full-rebate edge:

```bash
curl -s -X POST http://localhost:8000/api/v2/calc/preview \
  -H "Content-Type: application/json" \
  -d '{"gross_income":700000,"deductions":{},"regime":"new","is_salary_income":true,"fy":"<new_fy>"}' \
  | python -m json.tool
# total_tax should be 0 if the 87A threshold is 7L; non-zero if it moved.
```

A RAG search confirms the new rulebook chunks are reachable:

```bash
curl -s "http://localhost:8000/api/v2/rag/search?q=standard+deduction&k=3" | python -m json.tool
# Expect chunks mentioning the NEW standard deduction value, not the old one.
```

---

## Checklist

Copy this into a PR description for the FY migration.

- [ ] Confirmed Finance Act has been passed (not just Budget speech)
- [ ] Added `*_FY_<new>` constants in `backend/app/services/tax_engine_in_constants.py`
- [ ] Added new FY string to `SUPPORTED_FYS`
- [ ] Updated FY-dispatch in `backend/app/services/tax_engine_in.py` to route on `fy` arg
- [ ] Bumped default `fy` argument in every engine function
- [ ] Updated `backend/tax_rules.txt` header line
- [ ] Section 1 (new regime slabs) reviewed
- [ ] Section 2 (old regime slabs) reviewed
- [ ] Section 3 (standard deduction) reviewed
- [ ] Sections 4 / 5 (80C / 80D caps) reviewed
- [ ] Section 6 (87A rebate) reviewed
- [ ] Section 7 (surcharge bands) reviewed
- [ ] Section 16 (filing deadline) updated to new AY dates
- [ ] Section 17 (advance tax due dates) updated to new FY
- [ ] Section 23 (senior citizen slabs) reviewed
- [ ] Section 24 (87A marginal relief example) recomputed
- [ ] Section 29 (Budget summary) replaced with new year's changes
- [ ] `test_tax_engine_in.py` parametrize blocks and `total_tax` assertions updated or duplicated
- [ ] `test_metamorphic.py` - mock fallback values still sensible
- [ ] `assessment_year` default bumped in `backend/app/api/filing_v2.py`
- [ ] `CalcPreviewRequest.fy` default bumped
- [ ] `ChatStartRequest.initial_message` AY literal bumped
- [ ] PDF template / JSON builder reviewed against new ITR-1 schema (if changed)
- [ ] `_INTERVIEWER_SYSTEM_PROMPT` AY / regime literals updated (if changed)
- [ ] `python -m app.rag.ingest` re-run; chunk count printed
- [ ] `python -m pytest tests/ -q` green
- [ ] `/api/v2/calc/preview` smoke curl returns expected `total_tax`
- [ ] `/api/v2/rag/search` returns chunks with new values, not stale ones
