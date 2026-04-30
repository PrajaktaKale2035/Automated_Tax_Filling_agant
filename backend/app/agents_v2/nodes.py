"""
LangGraph Agent Nodes for the Indian Tax Filing Workflow.

Operates on TaxFilingState. Phase 0/1: calculator uses tax_engine_in,
researcher uses pgvector RAG, interviewer extracts structured fields via
JSON output, auditor validates the new TaxBreakdown shape.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.websockets.manager import manager

from .state import TaxFilingState


def _openai_api_key() -> str:
    """Resolve the OpenAI key. Backend uses OPENAI_API_KEY; tolerate VITE_ prefix
    used in some shared .env files."""
    return os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY") or ""


# ----------------------------------------------------------------------------
# Node 1: Interviewer - structured extraction from natural language
# ----------------------------------------------------------------------------

_INTERVIEWER_SYSTEM = SystemMessage(content="""\
You are a tax filing assistant for INDIAN ITR-1 (FY 2024-25 / AY 2025-26).
Extract any of these fields the user has mentioned and return them as JSON:
- income_salary (integer INR)
- income_other (integer INR)
- age (integer)
- filing_status ("individual" or "huf")
- regime ("old" or "new")
- deductions_80c (integer INR; 80C is OLD regime only)
- deductions_80d (integer INR; 80D is OLD regime only)
- pan (string, e.g. ABCDE1234F)

Output format: a single JSON object on the LAST line of your reply, prefixed
with `EXTRACTION:`. Above that line, reply conversationally - acknowledge what
the user said and ask for any missing information needed to compute their tax.

Example final line:
EXTRACTION: {"income_salary": 1200000, "regime": "old"}
""")


def _parse_extraction(text: str) -> Dict[str, Any]:
    """Pull the JSON object from the EXTRACTION: line. Returns {} on failure."""
    if not text:
        return {}
    m = re.search(r"EXTRACTION:\s*(\{.*\})", text, flags=re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


async def interviewer_node(state: TaxFilingState) -> Dict[str, Any]:
    """Extract structured user data from the conversation history."""
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.3,
        api_key=_openai_api_key(),
    )

    messages = [_INTERVIEWER_SYSTEM] + list(state.get("messages", []))
    response = llm.invoke(messages)

    extracted = _parse_extraction(response.content)
    user_profile = dict(state.get("user_profile") or {})
    user_profile.update(extracted)

    new_state: Dict[str, Any] = {
        "messages": [AIMessage(content=response.content)],
        "user_profile": user_profile,
        "current_agent": "interviewer",
    }
    if "regime" in extracted:
        new_state["regime"] = extracted["regime"]

    try:
        await manager.broadcast({
            "type": "agent_activity",
            "agent": "Interviewer",
            "message": f"Extracted {len(extracted)} field(s) from conversation.",
        })
    except Exception:
        pass

    return new_state


# ----------------------------------------------------------------------------
# Node 2: Researcher - real RAG over pgvector
# ----------------------------------------------------------------------------

async def researcher_node(state: TaxFilingState) -> Dict[str, Any]:
    """Query the pgvector-backed Indian tax rulebook for relevant chunks."""
    from app.rag.retriever import TaxRetriever

    profile = state.get("user_profile") or {}
    regime = state.get("regime") or profile.get("regime") or "new"
    income = int(profile.get("income_salary", 0) or 0)
    age = int(profile.get("age", 30) or 30)

    query = (
        f"Indian income tax rules for salary income {income} INR, "
        f"{regime} regime, age {age}. Slabs, deductions 80C, 80D, "
        f"rebate 87A, surcharge, and cess."
    )

    retriever = TaxRetriever()
    chunks = retriever.retrieve(query, k=6)

    research_results = [
        {
            "section": c.topic or "general",
            "description": c.content,
            "source": c.source,
            "score": c.score,
        }
        for c in chunks
    ]

    try:
        await manager.broadcast({
            "type": "agent_activity",
            "agent": "Researcher",
            "message": f"Retrieved {len(research_results)} rulebook chunks for {regime} regime.",
        })
    except Exception:
        pass

    return {
        "research_results": research_results,
        "current_agent": "researcher",
    }


# ----------------------------------------------------------------------------
# Node 3: Calculator - deterministic tax computation (no LLM math)
# ----------------------------------------------------------------------------

async def calculator_node(state: TaxFilingState) -> Dict[str, Any]:
    """Call tax_engine_in.compute_filing() with the extracted profile."""
    from app.services.tax_engine_in import compute_filing

    profile = state.get("user_profile") or {}
    regime = state.get("regime") or profile.get("regime") or "new"

    breakdown = compute_filing(
        gross_income=int(profile.get("income_salary", 0) or 0),
        deductions={
            "80c": int(profile.get("deductions_80c", 0) or 0),
            "80d": int(profile.get("deductions_80d", 0) or 0),
        },
        regime=regime,
        is_salary_income=True,
    )

    breakdown_dict = breakdown.to_dict()

    try:
        await manager.broadcast({
            "type": "agent_activity",
            "agent": "Calculator",
            "message": f"Computed total tax: Rs {breakdown.total_tax} ({regime} regime)",
        })
    except Exception:
        pass

    return {
        "tax_breakdown": breakdown_dict,
        "calculation_result": breakdown_dict,
        "regime": regime,
        "current_agent": "calculator",
    }


# ----------------------------------------------------------------------------
# Node 4: Auditor - validates TaxBreakdown invariants
# ----------------------------------------------------------------------------

async def auditor_node(state: TaxFilingState) -> Dict[str, Any]:
    """Property-based validation against the actual TaxBreakdown shape."""
    breakdown = state.get("tax_breakdown") or state.get("calculation_result") or {}
    errors: list[str] = []

    gross = float(breakdown.get("gross_income", 0) or 0)
    taxable = float(breakdown.get("taxable_income", 0) or 0)
    slab_tax = float(breakdown.get("slab_tax", 0) or 0)
    rebate = float(breakdown.get("rebate_87a", 0) or 0)
    after_rebate = float(breakdown.get("tax_after_rebate", 0) or 0)
    surcharge = float(breakdown.get("surcharge", 0) or 0)
    cess = float(breakdown.get("cess", 0) or 0)
    total_tax = float(breakdown.get("total_tax", 0) or 0)

    # Property 1: taxable income cannot exceed gross income.
    if taxable > gross:
        errors.append("Taxable income exceeds gross income")

    # Property 2: every component is non-negative.
    for name, value in (
        ("slab_tax", slab_tax), ("rebate_87a", rebate), ("tax_after_rebate", after_rebate),
        ("surcharge", surcharge), ("cess", cess), ("total_tax", total_tax),
    ):
        if value < 0:
            errors.append(f"Negative {name} detected ({value})")

    # Property 3: total_tax = tax_after_rebate + surcharge + cess (within rounding tolerance).
    expected_total = after_rebate + surcharge + cess
    if abs(expected_total - total_tax) > 1:
        errors.append(
            f"total_tax {total_tax} != after_rebate({after_rebate}) + "
            f"surcharge({surcharge}) + cess({cess}) = {expected_total}"
        )

    # Property 4: rebate cannot exceed slab_tax.
    if rebate > slab_tax + 0.01:
        errors.append(f"Rebate {rebate} exceeds slab_tax {slab_tax}")

    # Property 5: effective rate (total_tax / gross) sanity check.
    if gross > 0:
        effective_rate = total_tax / gross * 100.0
        if effective_rate > 50:
            errors.append(f"Effective tax rate {effective_rate:.1f}% exceeds 50% sanity cap")

    audit_status = "passed" if not errors else "failed"

    try:
        await manager.broadcast({
            "type": "agent_activity",
            "agent": "Auditor",
            "message": f"Audit {audit_status}. {len(errors)} issue(s) found.",
        })
    except Exception:
        pass

    return {
        "audit_status": audit_status,
        "audit_errors": errors if errors else None,
        "current_agent": "auditor",
    }
