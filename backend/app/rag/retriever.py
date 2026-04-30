"""pgvector-backed retriever for the Indian tax rulebook.

Replaces the previous ChromaDB implementation. Cosine similarity is computed
via pgvector's `<=>` operator on the `embedding` column.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import RagDocument


_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_COLLECTION = "itr_rulebook"


@dataclass
class RetrievedChunk:
    content: str
    source: str
    topic: Optional[str]
    score: float  # cosine similarity in [0, 1]; higher is more relevant.

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "topic": self.topic,
            "score": round(self.score, 4),
        }


class TaxRetriever:
    """Retrieve top-k Indian-tax-rulebook chunks for a query.

    The encoder is loaded once per instance; reuse instances when retrieving
    multiple times - SentenceTransformer init costs ~1s.
    """

    def __init__(
        self,
        model_name: str = _MODEL_NAME,
        collection: str = _DEFAULT_COLLECTION,
    ):
        self._model = SentenceTransformer(model_name)
        self._collection = collection

    def retrieve(
        self,
        query: str,
        k: int = 5,
        topic_filter: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> list[RetrievedChunk]:
        if not query or not query.strip():
            return []
        own_session = db is None
        session = db or SessionLocal()
        try:
            vec = self._model.encode(query, normalize_embeddings=True).tolist()
            distance_expr = RagDocument.embedding.cosine_distance(vec)
            q = (
                session.query(RagDocument, distance_expr.label("distance"))
                .filter(RagDocument.collection == self._collection)
            )
            if topic_filter:
                q = q.filter(RagDocument.topic == topic_filter)
            rows = q.order_by(distance_expr).limit(k).all()
            return [
                RetrievedChunk(
                    content=doc.content,
                    source=doc.source,
                    topic=doc.topic,
                    score=max(0.0, 1.0 - float(distance)),
                )
                for doc, distance in rows
            ]
        finally:
            if own_session:
                session.close()


def retrieve_itr_rules(
    query: str,
    k: int = 5,
    topic_filter: Optional[str] = None,
) -> list[RetrievedChunk]:
    """Convenience wrapper for one-off retrieval calls.

    For high-frequency callers (e.g., LangGraph nodes), prefer instantiating a
    single `TaxRetriever` and reusing it to avoid repeated model loads.
    """
    return TaxRetriever().retrieve(query, k=k, topic_filter=topic_filter)


if __name__ == "__main__":
    import sys
    # Use UTF-8 stdout so the rupee symbol doesn't crash on Windows cp932.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    r = TaxRetriever()
    for q in ["What is the standard deduction in new regime?",
              "Section 80C limit",
              "Surcharge for 1 crore income"]:
        print(f"\n>> {q}")
        for c in r.retrieve(q, k=3):
            print(f"  [{c.score:.3f}] {c.topic or '-':<18} {c.content[:80]}")
