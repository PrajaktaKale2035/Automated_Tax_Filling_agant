"""Ingest Indian tax rulebook content into the pgvector-backed `rag_documents` table.

Phase 1: ingests the curated `tax_rules.txt` (FY 2024-25 / AY 2025-26).
Future runs should add real IT Dept PDFs (Income Tax Act 1961 chapters,
ITR-1 instructions, Finance Act 2024, CBDT circulars on 80C/80D).

Embedding model: SentenceTransformer all-MiniLM-L6-v2 (384 dim).
Storage: pgvector cosine similarity on `rag_documents.embedding`.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer

from app.database import SessionLocal
from app.models import RagDocument


_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_DATA_FILE = Path(__file__).resolve().parents[2] / "tax_rules.txt"
_DEFAULT_COLLECTION = "itr_rulebook"

# Two tiers. Specific terms always win over generic ones, regardless of count.
# Within a tier, ties on count break by priority order.
_SPECIFIC_KEYWORDS: list[tuple[str, str]] = [
    # Cess
    ("cess",                 "cess"),
    ("health and education", "cess"),
    # Marginal relief — placed BEFORE 87a so dedicated marginal section wins
    ("marginal relief",      "marginal-relief"),
    # Rebate / surcharge
    ("87a",                  "rebate-87a"),
    ("rebate",               "rebate-87a"),
    ("surcharge",            "surcharge"),
    # Chapter VI-A deductions
    ("80c",                  "80C"),
    ("80ccd",                "80CCD"),
    ("nps",                  "80CCD"),
    ("national pension",     "80CCD"),
    ("80d",                  "80D"),
    ("80g",                  "80G"),
    ("donation",             "80G"),
    ("80tta",                "80TTA"),
    ("80ttb",                "80TTA"),
    # Salary-side exemptions (Section 10 / Section 16)
    ("lta",                  "lta"),
    ("leave travel",         "lta"),
    ("professional tax",     "professional-tax"),
    ("gratuity",             "gratuity"),
    ("leave encashment",     "gratuity"),
    # HRA / house property (before itr-1 so "house property" section wins)
    ("hra",                  "hra"),
    ("house rent",           "hra"),
    ("house property",       "house-property"),
    ("24b",                  "house-property"),
    ("self-occupied",        "house-property"),
    # Senior citizen slabs (after 80D so 80D senior-citizen mentions don't get hijacked)
    ("super senior",         "senior-citizen"),
    ("senior citizen",       "senior-citizen"),
    # Regime comparison / new-regime exclusions
    ("break-even",           "regime-comparison"),
    ("when to choose",       "regime-comparison"),
    ("115bac",               "new-regime-exclusions"),
    ("disallowed",           "new-regime-exclusions"),
    # TDS / Form 16 / AIS / identity
    ("form 16",              "form-16"),
    ("tds",                  "tds"),
    ("standard deduction",   "standard-deduction"),
    ("26as",                 "ais-26as"),
    ("annual information",   "ais-26as"),
    ("pan",                  "identity"),
    ("aadhaar",              "identity"),
    # Deadline / advance tax / e-verification
    ("234f",                 "deadline"),
    ("july 31",              "deadline"),
    ("belated",              "deadline"),
    ("advance tax",          "advance-tax"),
    ("234b",                 "advance-tax"),
    ("234c",                 "advance-tax"),
    ("e-verification",       "e-verification"),
    ("itr-v",                "e-verification"),
    # Budget / Finance Act
    ("budget 2024",          "budget-2024"),
    ("finance act 2024",     "budget-2024"),
    # Eligibility (last so more-specific topics above win)
    ("itr-1",                "itr1-eligibility"),
    ("sahaj",                "itr1-eligibility"),
]

_GENERIC_KEYWORDS: list[tuple[str, str]] = [
    ("regime",  "slabs"),
    ("slab",    "slabs"),
]


def _best_match(text: str, table: list[tuple[str, str]]) -> tuple[Optional[str], int]:
    """Return (topic, count) for whichever keyword in `table` has the most
    word-boundary occurrences in `text`. Ties broken by priority order."""
    best_topic: Optional[str] = None
    best_count = 0
    best_priority = 1 << 30
    for priority, (needle, topic) in enumerate(table):
        pattern = r"\b" + re.escape(needle) + r"\b"
        count = len(re.findall(pattern, text))
        if count == 0:
            continue
        if count > best_count or (count == best_count and priority < best_priority):
            best_count = count
            best_priority = priority
            best_topic = topic
    return best_topic, best_count


def _infer_topic(text: str) -> Optional[str]:
    """Specific topic always wins over generic. Word-boundary match prevents
    substring false positives ('cess' matching inside 'excess'). Used at
    ingest time to populate `rag_documents.topic`."""
    lowered = text.lower()
    specific, _ = _best_match(lowered, _SPECIFIC_KEYWORDS)
    if specific is not None:
        return specific
    generic, _ = _best_match(lowered, _GENERIC_KEYWORDS)
    return generic


def _chunk_paragraphs(text: str) -> list[str]:
    """Split by blank lines, keeping semantic paragraph boundaries."""
    chunks = re.split(r"\n\s*\n", text)
    return [c.strip() for c in chunks if c.strip()]


def ingest_text(
    raw_text: str,
    *,
    source: str,
    collection: str = _DEFAULT_COLLECTION,
    model_name: str = _MODEL_NAME,
    replace_collection: bool = True,
) -> int:
    """Embed `raw_text` (split into paragraphs) and write rows to `rag_documents`.

    Returns the number of rows written.
    """
    chunks = _chunk_paragraphs(raw_text)
    if not chunks:
        return 0

    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True)

    db = SessionLocal()
    try:
        if replace_collection:
            db.query(RagDocument).filter(RagDocument.collection == collection).delete()
            db.commit()

        for idx, (chunk, vec) in enumerate(zip(chunks, embeddings)):
            db.add(RagDocument(
                collection=collection,
                source=source,
                chunk_index=idx,
                topic=_infer_topic(chunk),
                content=chunk,
                embedding=vec.tolist(),
                extra_metadata={"model": model_name, "char_len": len(chunk)},
            ))
        db.commit()
        return len(chunks)
    finally:
        db.close()


def ingest_file(
    path: os.PathLike | str = _DEFAULT_DATA_FILE,
    *,
    collection: str = _DEFAULT_COLLECTION,
    model_name: str = _MODEL_NAME,
    replace_collection: bool = True,
) -> int:
    """Ingest a single text file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"data file not found: {path}")
    text = path.read_text(encoding="utf-8")
    return ingest_text(
        text,
        source=path.name,
        collection=collection,
        model_name=model_name,
        replace_collection=replace_collection,
    )


def ingest_directory(
    directory: os.PathLike | str,
    *,
    collection: str = _DEFAULT_COLLECTION,
    model_name: str = _MODEL_NAME,
    replace_collection: bool = True,
    pattern: str = "*.txt",
) -> int:
    """Ingest every file matching `pattern`. Clears collection only before the first file."""
    directory = Path(directory)
    files = sorted(directory.glob(pattern))
    if not files:
        return 0
    total = 0
    for i, path in enumerate(files):
        total += ingest_text(
            path.read_text(encoding="utf-8"),
            source=path.name,
            collection=collection,
            model_name=model_name,
            replace_collection=(replace_collection and i == 0),
        )
    return total


if __name__ == "__main__":
    import argparse
    import sys

    # Ensure UTF-8 output so rupee / special chars don't crash on Windows cp932.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="python -m app.rag.ingest",
        description=(
            "Ingest content into the pgvector ITR rulebook collection.\n\n"
            "With no flags, ingests the default tax_rules.txt (FY 2024-25 / AY 2025-26)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m app.rag.ingest                          # default tax_rules.txt\n"
            "  python -m app.rag.ingest --list                   # show what is in the DB\n"
            "  python -m app.rag.ingest --file my_rules.txt      # replace with custom file\n"
            "  python -m app.rag.ingest --file extra.txt --append # add without wiping\n"
            "  python -m app.rag.ingest --dir docs/ --pattern *.txt --append\n"
            "  python -m app.rag.ingest --pdf income_tax_act.pdf  # requires: pip install pypdf\n"
            "  python -m app.rag.ingest --collection custom_kb --file kb.txt\n"
        ),
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--file", metavar="PATH",
        help="Ingest a single .txt file (replaces collection unless --append)",
    )
    source.add_argument(
        "--dir", metavar="PATH",
        help="Ingest every file matching --pattern inside a directory",
    )
    source.add_argument(
        "--pdf", metavar="PATH",
        help="Ingest a text-based PDF (requires: pip install pypdf). "
             "Scanned/image PDFs produce no text - run Tesseract OCR first.",
    )
    source.add_argument(
        "--list", action="store_true",
        help="Print all chunks currently stored in the collection and exit",
    )

    parser.add_argument(
        "--collection", default=_DEFAULT_COLLECTION, metavar="NAME",
        help=f"Collection name to read/write (default: {_DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--pattern", default="*.txt", metavar="GLOB",
        help="File glob pattern used with --dir (default: *.txt)",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Add chunks to the collection instead of replacing it",
    )

    args = parser.parse_args()
    replace = not args.append

    # ---- --list --------------------------------------------------------------
    if args.list:
        from app.database import SessionLocal
        from app.models import RagDocument as _RD
        _db = SessionLocal()
        rows = (
            _db.query(_RD.source, _RD.topic, _RD.chunk_index)
            .filter(_RD.collection == args.collection)
            .order_by(_RD.source, _RD.chunk_index)
            .all()
        )
        _db.close()
        if not rows:
            print(f"Collection '{args.collection}' is empty (or does not exist).")
        else:
            print(f"Collection '{args.collection}' - {len(rows)} chunk(s):")
            for r in rows:
                print(f"  [{r.chunk_index:>3}]  {r.source:<40}  topic={r.topic or '-'}")
        sys.exit(0)

    # ---- --pdf ---------------------------------------------------------------
    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)
        try:
            from pypdf import PdfReader
        except ImportError:
            print(
                "ERROR: PDF ingestion requires pypdf.\n"
                "  pip install pypdf\n"
                "Then re-run this command.\n"
                "\nTip: pypdf works on text-based PDFs only. For scanned PDFs\n"
                "(Form 16 images, etc.) use the /api/documents/upload endpoint\n"
                "which runs Tesseract OCR automatically.",
                file=sys.stderr,
            )
            sys.exit(1)
        reader = PdfReader(str(pdf_path))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            print(
                "WARNING: no text extracted from PDF. It may be a scanned/image PDF.\n"
                "Use Tesseract OCR (via /api/documents/upload) instead.",
                file=sys.stderr,
            )
            sys.exit(1)
        n = ingest_text(
            text,
            source=pdf_path.name,
            collection=args.collection,
            replace_collection=replace,
        )
        print(f"Ingested {n} chunk(s) from PDF '{pdf_path.name}' into '{args.collection}'.")
        sys.exit(0)

    # ---- --dir ---------------------------------------------------------------
    if args.dir:
        n = ingest_directory(
            args.dir,
            collection=args.collection,
            pattern=args.pattern,
            replace_collection=replace,
        )
        print(
            f"Ingested {n} chunk(s) from '{args.dir}' "
            f"(pattern={args.pattern}) into '{args.collection}'."
        )
        sys.exit(0)

    # ---- --file or default ---------------------------------------------------
    target = Path(args.file) if args.file else _DEFAULT_DATA_FILE
    n = ingest_file(target, collection=args.collection, replace_collection=replace)
    print(f"Ingested {n} chunk(s) from '{target.name}' into '{args.collection}'.")
