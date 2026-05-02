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

from app.websockets.manager import manager

from .state import TaxFilingState


def _clean_key(value: str) -> str:
    """Treat empty / placeholder values as missing keys."""
    if not value:
        return ""
    v = value.strip()
    if not v or v.startswith("your_") or v.endswith("_here"):
        return ""
    return v


def _openai_api_key() -> str:
    """Resolve the OpenAI key. Backend uses OPENAI_API_KEY; tolerate VITE_ prefix
    used in some shared .env files."""
    return _clean_key(os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY") or "")


def _gemini_api_key() -> str:
    """Resolve the Gemini key. Both GEMINI_API_KEY and GOOGLE_API_KEY are accepted
    since different Google libraries read different names."""
    return _clean_key(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "")


def _build_llm(temperature: float = 0.3):
    """Pick an LLM based on LLM_PROVIDER env var or available API keys.

    Selection priority:
      1. LLM_PROVIDER='ollama'  → local Ollama (no key needed)
      2. LLM_PROVIDER='gemini'  → Google Gemini API
      3. LLM_PROVIDER='openai'  → OpenAI API
      4. Auto-detect: OpenAI key present → OpenAI
      5. Auto-detect: Gemini key present → Gemini
      6. Fallback                → Ollama (fully local, no key required)

    Env vars:
      LLM_PROVIDER     : 'ollama' | 'gemini' | 'openai'  (optional)
      OLLAMA_MODEL     : default 'mistral'
      OLLAMA_BASE_URL  : default 'http://localhost:11434'
      GEMINI_MODEL     : default 'gemini-flash-lite-latest'
      OPENAI_MODEL     : default 'gpt-4'
    """
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    openai_key = _openai_api_key()
    gemini_key = _gemini_api_key()

    # ---- Ollama (local, no API key needed) ----------------------------------
    if provider == "ollama" or (not provider and not openai_key and not gemini_key):
        from langchain_ollama import ChatOllama
        model = os.getenv("OLLAMA_MODEL", "mistral")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model=model, temperature=temperature, base_url=base_url)

    # ---- Gemini API ---------------------------------------------------------
    if provider == "gemini" or (not provider and not openai_key and gemini_key):
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        # max_retries=0 so 429/503 surfaces immediately instead of looping for
        # minutes and timing out the UI fetch.
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=gemini_key,
            max_retries=0,
        )

    # ---- OpenAI API ---------------------------------------------------------
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        temperature=temperature,
        api_key=openai_key,
    )


# ----------------------------------------------------------------------------
# Node 1: Interviewer - structured extraction from natural language
# ----------------------------------------------------------------------------

_INTERVIEWER_SYSTEM_PROMPT = """\
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
When answering tax rule questions, cite specific amounts from the rulebook context below.

Example final line:
EXTRACTION: {"income_salary": 1200000, "regime": "old"}
"""


def _build_interviewer_messages(state: "TaxFilingState", llm: Any) -> list:
    """Build the LLM message list for the interviewer, injecting RAG context.

    research_results from the previous graph turn are appended to the system
    prompt so the LLM can give rulebook-grounded answers (e.g. exact cess
    rate, 87A threshold, 80C cap) instead of relying on training-data memory.
    """
    history = list(state.get("messages", []))

    research_results = state.get("research_results") or []
    if research_results:
        snippets = "\n".join(
            f"  [{r.get('section', 'general')}] {r.get('description', '')[:300]}"
            for r in research_results[:5]
        )
        rag_block = (
            "\n\n--- Relevant ITR Rulebook (cite these when answering tax questions) ---\n"
            + snippets
            + "\n---"
        )
    else:
        rag_block = ""

    system_content = _INTERVIEWER_SYSTEM_PROMPT + rag_block

    model_name = (getattr(llm, "model", "") or "").lower()
    if "gemma" in model_name and history:
        first = history[0]
        merged = HumanMessage(
            content=f"{system_content}\n\n---\n\nUser: {first.content}"
        )
        return [merged] + history[1:]
    return [SystemMessage(content=system_content)] + history


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


def _response_text(response: Any) -> str:
    """Normalize LangChain LLM response content to a plain string.

    OpenAI returns `content` as a string; Gemini returns it as a list of
    {'type': 'text', 'text': ...} blocks. Concatenate the text parts.
    """
    content = getattr(response, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content or "")


async def interviewer_node(state: TaxFilingState) -> Dict[str, Any]:
    """Extract structured user data; grounds answers in ITR rulebook via RAG context.

    LLM errors (quota exhausted, model unavailable) are caught and returned as
    a friendly message so the graph continues to the researcher node and the
    RAG sidebar still populates even when the LLM is down.
    """
    import asyncio as _aio

    response_text = ""
    try:
        # _build_llm and _build_interviewer_messages are inside the try so that
        # any httpx/transport error during model init is also caught gracefully.
        llm = _build_llm(temperature=0.3)
        messages = _build_interviewer_messages(state, llm)
        # ainvoke (async) with a 30s timeout so a stale Gemini connection never
        # blocks the event loop indefinitely.
        response = await _aio.wait_for(llm.ainvoke(messages), timeout=30.0)
        response_text = _response_text(response)
    except _aio.TimeoutError:
        response_text = (
            "⚠️ LLM timed out (>30s). Returning RAG results only — "
            "check the rulebook sources on the right for your answer."
        )
    except Exception as llm_err:
        err_msg = str(llm_err)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
            response_text = (
                "⚠️ LLM quota exhausted. Returning RAG results only — "
                "check the rulebook sources on the right for your answer."
            )
        elif "503" in err_msg or "UNAVAILABLE" in err_msg or "disconnected" in err_msg.lower():
            response_text = (
                "⚠️ LLM temporarily unavailable. Showing RAG sources only — "
                "please retry in a moment."
            )
        else:
            response_text = f"⚠️ LLM error: {err_msg[:120]}. RAG sources are still available on the right."

    extracted = _parse_extraction(response_text)
    user_profile = dict(state.get("user_profile") or {})
    user_profile.update(extracted)

    new_state: Dict[str, Any] = {
        "messages": [AIMessage(content=response_text)],
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
    """Query the pgvector-backed Indian tax rulebook via LangChain retriever."""
    from app.rag.retriever import get_langchain_retriever

    profile = state.get("user_profile") or {}
    regime = state.get("regime") or profile.get("regime") or "new"
    income = int(profile.get("income_salary", 0) or 0)
    age = int(profile.get("age", 30) or 30)

    # Use the user's own message text as the primary signal so off-topic
    # questions (e.g. cess) actually retrieve the relevant chunks. Fall back
    # to the structured profile-based query when no message is present.
    history = state.get("messages") or []
    last_user = next(
        (m for m in reversed(history) if m.__class__.__name__ == "HumanMessage"),
        None,
    )
    user_text = (getattr(last_user, "content", "") or "").strip() if last_user else ""
    if user_text:
        query = user_text
    else:
        query = (
            f"Indian income tax rules for salary income {income} INR, "
            f"{regime} regime, age {age}. Slabs, deductions 80C, 80D, "
            f"rebate 87A, surcharge, and cess."
        )

    # LangChain retriever: ainvoke runs _aget_relevant_documents which uses
    # asyncio.to_thread internally — no blocking the event loop.
    retriever = get_langchain_retriever(k=6)
    docs = await retriever.ainvoke(query)

    research_results = [
        {
            "section": doc.metadata.get("topic") or "general",
            "description": doc.page_content,
            "source": doc.metadata.get("source", ""),
            "score": doc.metadata.get("score", 0.0),
        }
        for doc in docs
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
