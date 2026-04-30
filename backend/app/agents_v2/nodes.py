"""
LangGraph Agent Nodes for Tax Filing Workflow

These nodes operate on TaxFilingState and are orchestrated by the graph.
They run in PARALLEL to the existing LangChain agents in src/agents/
"""
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from .state import TaxFilingState
import os
from app.websockets.manager import manager


# ============================================================================
# Node 1: Interviewer Agent (Frontend Interface)
# ============================================================================

async def interviewer_node(state: TaxFilingState) -> Dict[str, Any]:
    """
    Extracts structured user data from natural language conversation.
    
    Role: The empathetic interface that asks clarifying questions
    Tech: GPT-4 with function calling to extract structured fields
    
    Args:
        state: Current graph state with conversation history
    
    Returns:
        Updated state with extracted user_profile
    """
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0.3,
        api_key=os.getenv("VITE_OPENAI_API_KEY")
    )
    
    # System prompt for structured extraction
    system_prompt = SystemMessage(content="""
    You are a tax filing assistant. Your job is to extract structured information 
    from the user's messages. Extract:
    - income_salary (float)
    - income_other (float) 
    - age (int)
    - filing_status (string: "individual" | "huf")
    - regime (string: "old" | "new")
    - deductions_80c (float, if mentioned)
    
    Respond in a friendly manner and ask for missing information.
    """)
    
    messages = [system_prompt] + state.get("messages", [])
    
    # Call LLM (simplified - in production, use function calling)
    response = llm.invoke(messages)
    
    # Parse response into user_profile (simplified)
    user_profile = state.get("user_profile", {})
    # TODO: Implement proper extraction logic
    user_profile["_last_message"] = response.content
    
    user_profile["_last_message"] = response.content
    
    await manager.broadcast({
        "type": "agent_activity",
        "agent": "Interviewer",
        "message": "Extracted user profile data from conversation."
    })
    
    return {
        "messages": [AIMessage(content=response.content)],
        "user_profile": user_profile,
        "current_agent": "interviewer"
    }


# ============================================================================
# Node 2: Researcher Agent (GraphRAG)
# ============================================================================

async def researcher_node(state: TaxFilingState) -> Dict[str, Any]:
    """Real RAG over the IT Department rulebook (pgvector + SentenceTransformer).

    Phase 1: queries the `rag_documents` table for chunks relevant to the
    user's profile. Pulls per-topic context (slabs, 80C, 80D, surcharge, cess)
    so the calculator and auditor can ground their explanations in the rulebook.
    """
    from app.rag.retriever import TaxRetriever

    profile = state.get("user_profile") or {}
    regime = state.get("regime") or profile.get("regime") or "new"
    income = int(profile.get("income_salary", 0) or 0)
    age = int(profile.get("age", 30) or 30)

    # Compose a query from the user context.
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


# ============================================================================
# Node 3: Calculator Agent (Rust Engine Wrapper)
# ============================================================================

async def calculator_node(state: TaxFilingState) -> Dict[str, Any]:
    """Deterministic Indian tax computation. NO LLM math.

    Phase 0: calls services.tax_engine_in.compute_filing() with full
    old/new regime support, 80C/80D deductions (old regime), rebate 87A,
    surcharge bands, and 4% cess.
    """
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
        # WebSocket broadcast is best-effort; never block calc on it.
        pass

    return {
        "tax_breakdown": breakdown_dict,
        "calculation_result": breakdown_dict,
        "regime": regime,
        "current_agent": "calculator",
    }


# ============================================================================
# Node 4: Auditor Agent (Metamorphic Testing)
# ============================================================================

async def auditor_node(state: TaxFilingState) -> Dict[str, Any]:
    """
    Validates the tax draft against legal invariants.
    
    Role: Internal QA that checks for logical inconsistencies
    Tech: Metamorphic testing (property-based validation)
    
    Args:
        state: Current graph state with calculation_result
    
    Returns:
        Updated state with audit_status and audit_errors
    """
    calculation = state.get("calculation_result", {})
    user_profile = state.get("user_profile", {})
    
    errors = []
    
    # Metamorphic Property 1: Deductions cannot exceed gross income
    gross = calculation.get("gross_income", 0)
    deductions = calculation.get("deductions", 0)
    if deductions > gross:
        errors.append("Deductions exceed gross income")
    
    # Metamorphic Property 2: Tax liability cannot be negative
    tax = calculation.get("tax_liability", 0)
    if tax < 0:
        errors.append("Negative tax liability detected")
    
    # Metamorphic Property 3: Taxable income should be non-negative
    taxable = calculation.get("taxable_income", 0)
    if taxable < 0:
        errors.append("Negative taxable income")
    
    # Metamorphic Property 4: Effective rate should be between 0-30%
    effective_rate = calculation.get("effective_tax_rate", 0)
    if effective_rate > 30:
        errors.append(f"Effective tax rate {effective_rate}% exceeds maximum 30%")
    
    audit_status = "passed" if len(errors) == 0 else "failed"
    
    audit_status = "passed" if len(errors) == 0 else "failed"
    
    await manager.broadcast({
        "type": "agent_activity",
        "agent": "Auditor",
        "message": f"Audit {audit_status}. {len(errors)} issues found."
    })
    
    return {
        "audit_status": audit_status,
        "audit_errors": errors if errors else None,
        "current_agent": "auditor"
    }
