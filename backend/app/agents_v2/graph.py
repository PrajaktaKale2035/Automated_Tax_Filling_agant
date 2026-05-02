"""
LangGraph Workflow Definition for Tax Filing

This is the "brain" of the Phase 1 architecture.
It orchestrates the 4 agent nodes in a cyclic, stateful manner.
"""
import asyncio

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from .state import TaxFilingState
from .nodes import interviewer_node, researcher_node, calculator_node, auditor_node


async def research_and_calc_node(state):
    """Run researcher + calculator in parallel - they share state but
    don't depend on each other's output."""
    research_result, calc_result = await asyncio.gather(
        researcher_node(state),
        calculator_node(state),
    )
    return {**research_result, **calc_result, "current_agent": "research_and_calc"}


# ============================================================================
# Conditional Routing Logic
# ============================================================================

def should_continue_to_end(state: TaxFilingState) -> str:
    """Always end after the auditor.

    Previously looped back to research_and_calc on audit failure, but the
    calculator is deterministic — re-running with the same profile produces
    the same result, causing an infinite loop to the recursion limit. Audit
    errors are surfaced in the API response for the frontend to display.
    """
    return "end"


def route_after_interviewer(state: TaxFilingState) -> str:
    """Always proceed to research_and_calc after the interviewer.

    Previously gated on income_salary + age being present, which meant purely
    informational questions ("What is HRA?") never reached the researcher and
    the RAG sidebar always showed empty. Now every message gets RAG context and
    a tax computation (calculator defaults to 0 income when not yet provided).
    """
    return "researcher"


# ============================================================================
# Build the State Machine Graph
# ============================================================================

def create_tax_filing_graph():
    """
    Creates the LangGraph workflow with PostgreSQL checkpointing.
    
    Graph Structure:
        START -> interviewer -> researcher -> calculator -> auditor
                      ↑              ↓
                      └──────────────┘ (if audit fails)
    
    Returns:
        Compiled StateGraph with checkpointing enabled
    """
    # Initialize the graph
    workflow = StateGraph(TaxFilingState)
    
    # Add nodes - research_and_calc fans out researcher+calculator in parallel
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("research_and_calc", research_and_calc_node)
    workflow.add_node("auditor", auditor_node)

    workflow.set_entry_point("interviewer")

    # interviewer -> research_and_calc (if data complete) OR stay in interviewer
    workflow.add_conditional_edges(
        "interviewer",
        route_after_interviewer,
        {
            "interviewer": "interviewer",
            "researcher": "research_and_calc",  # historical name kept in router
        },
    )

    workflow.add_edge("research_and_calc", "auditor")

    workflow.add_conditional_edges(
        "auditor",
        should_continue_to_end,
        {
            "researcher": "research_and_calc",
            "end": END,
        },
    )
    
    # Phase 0: in-memory checkpointing.
    # Phase 3 will switch to AsyncPostgresSaver with `async with` lifecycle
    # (the PostgresSaver context-manager API doesn't fit module-level wiring).
    checkpointer = InMemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


# ============================================================================
# Export the compiled graph
# ============================================================================

# This is the production-ready graph that can be invoked
tax_filing_graph = create_tax_filing_graph()
