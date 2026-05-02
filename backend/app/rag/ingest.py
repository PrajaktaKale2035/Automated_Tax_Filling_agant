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
    ("cess",                 "cess"),
    ("health and education", "cess"),
    ("87a",                  "rebate-87a"),
    ("rebate",               "rebate-87a"),
    ("surcharge",            "surcharge"),
    ("80c",                  "80C"),
    ("80d",                  "80D"),
    ("form 16",              "form-16"),
    ("tds",                  "tds"),
    ("standard deduction",   "standard-deduction"),
    ("pan",                  "identity"),
    ("aadhaar",              "identity"),
    ("itr-1",                "itr1-eligibility"),
    ("sahaj",                "itr1-eligibility"),
]

_GENERIC_KEYWORDS: list[tuple[str, str]] = [
    ("slab",   "slabs"),
    ("regime", "slabs"),
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
    n = ingest_file()
    print(f"Ingested {n} chunks from {_DEFAULT_DATA_FILE.name} into '{_DEFAULT_COLLECTION}'.")
