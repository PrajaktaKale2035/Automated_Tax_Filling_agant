"""
Phase 1 State Schema for LangGraph Tax Filing Workflow

This defines the shared state that flows through all agent nodes.
Keeps existing LangChain agents untouched.
"""
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph import add_messages
from datetime import datetime


class TaxFilingState(TypedDict):
    """
    Complete state for the tax filing graph workflow.
    
    This state is persisted to PostgreSQL at checkpoints,
    enabling long-running sessions and time-travel debugging.
    """
    # Conversation history (LangGraph managed)
    messages: Annotated[list, add_messages]
    
    # User profile extracted from conversation
    user_profile: Optional[Dict[str, Any]]  # {income, age, filing_status, etc.}
    
    # Current tax draft (ITR-1 structure)
    tax_draft: Optional[Dict[str, Any]]  # Matches ITR-1 schema
    
    # Research results from GraphRAG
    research_results: Optional[List[Dict[str, Any]]]  # Neo4j query results
    
    # Calculation results from Rust engine
    calculation_result: Optional[Dict[str, Any]]  # {tax_liability, deductions, etc.}
    
    # Audit status
    audit_status: Optional[str]  # "pending" | "passed" | "failed"
    audit_errors: Optional[List[str]]  # List of validation errors
    
    # Metadata
    thread_id: str  # Session identifier
    created_at: Optional[datetime]
    last_updated: Optional[datetime]
    current_agent: Optional[str]  # Which agent is currently executing

    # Phase 0 additions - Indian tax filing
    regime: Optional[str]                     # "old" | "new"
    form16_id: Optional[int]                  # FK to Form16 row (Phase 2)
    tax_breakdown: Optional[Dict[str, Any]]   # tax_engine_in.TaxBreakdown.to_dict()
    itr1_filing_id: Optional[int]             # FK to ITR1Filing row
    pdf_path: Optional[str]                   # Filesystem path to generated PDF


class UserProfile(TypedDict):
    """Structured user data extracted by interviewer agent"""
    income_salary: Optional[float]
    income_other: Optional[float]
    age: Optional[int]
    filing_status: Optional[str]  # "individual" | "huf" | etc.
    regime: Optional[str]  # "old" | "new"
    deductions_80c: Optional[float]
    deductions_80d: Optional[float]
    # ... more fields as needed


class TaxDraft(TypedDict):
    """ITR-1 Sahaj structure"""
    part_a_general_info: Optional[Dict[str, Any]]
    part_b_gross_total_income: Optional[Dict[str, Any]]
    part_c_deductions: Optional[Dict[str, Any]]
    part_d_tax_computation: Optional[Dict[str, Any]]
    status: Optional[str]  # "draft" | "in_progress" | "ready_to_file"
