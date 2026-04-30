"""Live integration tests for the pgvector-backed RAG.

These tests skip cleanly when Postgres + pgvector are unreachable. Phase 1
already verifies the happy path interactively via `python -m app.rag.retriever`.
"""
import pytest

# Try the real DB once at module load so we can skip the whole module if Postgres isn't up.
try:
    from sqlalchemy import text
    from app.database import SessionLocal
    _db = SessionLocal()
    _db.execute(text("SELECT 1"))
    _db.close()
    _PG_OK = True
except Exception:
    _PG_OK = False

pytestmark = pytest.mark.skipif(not _PG_OK, reason="Postgres not reachable - skipping pgvector RAG integration tests")


def test_retriever_returns_relevant_chunks_for_surcharge_query():
    """Surcharge query should return the surcharge paragraph as the top hit."""
    from app.rag.retriever import TaxRetriever
    r = TaxRetriever()
    chunks = r.retrieve("What is the surcharge for income above 1 crore?", k=3)
    assert len(chunks) >= 1
    top = chunks[0]
    assert "surcharge" in top.content.lower()
    assert top.score > 0.5


def test_retriever_returns_relevant_chunks_for_80c_query():
    from app.rag.retriever import TaxRetriever
    r = TaxRetriever()
    chunks = r.retrieve("Section 80C deduction limit", k=3)
    assert len(chunks) >= 1
    contents = " ".join(c.content for c in chunks).lower()
    assert "80c" in contents
    assert "1,50,000" in contents or "150000" in contents.replace(",", "")


def test_retriever_topic_filter_narrows_results():
    """Topic filter should constrain to a specific topic when set."""
    from app.rag.retriever import TaxRetriever
    r = TaxRetriever()
    chunks = r.retrieve("rebate", k=5, topic_filter="rebate-87a")
    # All returned chunks must have the requested topic.
    for c in chunks:
        assert c.topic == "rebate-87a"


def test_retriever_empty_query_returns_empty_list():
    from app.rag.retriever import TaxRetriever
    r = TaxRetriever()
    assert r.retrieve("") == []
    assert r.retrieve("   ") == []
