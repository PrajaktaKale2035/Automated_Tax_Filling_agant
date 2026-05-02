"""
LangGraph Workflow Definition for Tax Filing

This is the "brain" of the Phase 1 architecture.
It orchestrates the 4 agent nodes in a cyclic, stateful manner.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import TaxFilingState
import asyncio
from .nodes import interviewer_node, researcher_node, calculator_node, auditor_node


async def research_and_calc_node(state):
    """Run researcher + calculator in parallel - they share state but
    don't depend on each other's output."""
    research_result, calc_result = await asyncio.gather(
        researcher_node(state),
        calculator_node(state),
    )
    return {**research_result, **calc_result, "current_agent": "research_and_calc"}
import os


# ============================================================================
# Conditional Routing Logic
# ============================================================================

def should_continue_to_end(state: TaxFilingState) -> str:
    """
    Determines if the workflow should loop back or end.
    
    If audit fails, route back to researcher for re-evaluation.
    If audit passes, end the workflow.
    """
    audit_status = state.get("audit_status")
    
    if audit_status == "failed":
        # Audit found errors - route back to researcher
        return "researcher"
    else:
        # Audit passed - end workflow
        return "end"


def route_after_interviewer(state: TaxFilingState) -> str:
    """
    Determines if we have enough information to proceed.
    
    If user_profile is incomplete, stay in interviewer mode.
    Otherwise, proceed to researcher.
    """
    user_profile = state.get("user_profile", {})
    
    # Check if essential fields are present
    required_fields = ["income_salary", "age"]
    has_required = all(field in user_profile for field in required_fields)
    
    if has_required:
        return "researcher"
    else:
        # Need more information - stay in interviewer
        return "interviewer"


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
