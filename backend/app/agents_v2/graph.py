"""
LangGraph Workflow Definition for Tax Filing

This is the "brain" of the Phase 1 architecture.
It orchestrates the 4 agent nodes in a cyclic, stateful manner.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from .state import TaxFilingState
from .nodes import interviewer_node, researcher_node, calculator_node, auditor_node
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
    
    # Add nodes
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("calculator", calculator_node)
    workflow.add_node("auditor", auditor_node)
    
    # Set entry point
    workflow.set_entry_point("interviewer")
    
    # Define edges
    # Conditional: interviewer -> researcher (if data complete) OR stay in interviewer
    workflow.add_conditional_edges(
        "interviewer",
        route_after_interviewer,
        {
            "interviewer": "interviewer",  # Loop back if incomplete
            "researcher": "researcher"
        }
    )
    
    # Linear flow: researcher -> calculator -> auditor
    workflow.add_edge("researcher", "calculator")
    workflow.add_edge("calculator", "auditor")
    
    # Conditional: auditor -> END (if passed) OR -> researcher (if failed)
    workflow.add_conditional_edges(
        "auditor",
        should_continue_to_end,
        {
            "researcher": "researcher",  # Cycle back to re-research
            "end": END
        }
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
