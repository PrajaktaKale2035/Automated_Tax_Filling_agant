"""
LangGraph Workflow Definition for Tax Filing

This is the "brain" of the Phase 1 architecture.
It orchestrates the 4 agent nodes in a cyclic, stateful manner.
"""
import asyncio
import os

from langgraph.graph import StateGraph, END

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
    
    # Compile with InMemorySaver first — pool is opened later in lifespan
    from langgraph.checkpoint.memory import InMemorySaver
    app = workflow.compile(checkpointer=InMemorySaver())
    return app


# ============================================================================
# Module-level pool + graph — pool is opened by open_graph_pool() in lifespan
# ============================================================================

_graph_pool = None
_graph_checkpointer = None

def create_postgres_checkpointer():
    """Build (but don't open) the AsyncConnectionPool + AsyncPostgresSaver."""
    global _graph_pool, _graph_checkpointer
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        DATABASE_URL = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5436/taxdb",
        )
        _graph_pool = AsyncConnectionPool(
            DATABASE_URL,
            open=False,
            min_size=1,
            max_size=10,
            max_idle=300,           # close connections idle > 5 min
            max_lifetime=3600,      # recycle connections after 1 hour
            reconnect_timeout=30,   # retry broken connections for up to 30 s
            # Validate every connection before handing it out — without this,
            # the pool can return a TCP-dead socket and the caller hits
            # "consuming input failed: could not receive data from server"
            # mid-query. With it, dead connections are detected on getconn()
            # and a fresh one is opened transparently.
            check=AsyncConnectionPool.check_connection,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                # TCP keepalives — prevent Windows from aborting idle sockets
                "keepalives": 1,
                "keepalives_idle": 30,      # send first probe after 30 s idle
                "keepalives_interval": 10,  # retry probe every 10 s
                "keepalives_count": 5,      # drop after 5 unanswered probes
            },
        )
        _graph_checkpointer = AsyncPostgresSaver(_graph_pool)
        return _graph_checkpointer
    except Exception:
        return None


# Substring matchers for transient psycopg connection drops. We look at the
# stringified exception (psycopg sometimes wraps these) so we don't need to
# import the concrete OperationalError types.
_TRANSIENT_PG_MARKERS = (
    "consuming input failed",
    "could not receive data from server",
    "server closed the connection",
    "connection is bad",
    "connection is closed",
    "connection aborted",
    "connection reset",
    "10053",
    "10054",
    "broken pipe",
    "ssl connection has been closed unexpectedly",
)


def is_transient_pg_error(exc: BaseException) -> bool:
    """Return True if `exc` looks like a recoverable Postgres connection drop."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_PG_MARKERS)


async def refresh_pool() -> None:
    """Force the connection pool to discard dead sockets and re-validate.

    Called from the chat endpoints after we hit a transient connection error
    so the next attempt starts with known-good connections.
    """
    if _graph_pool is None:
        return
    try:
        await _graph_pool.check()
    except Exception:
        # Don't let pool refresh raise; the retry will surface the real error.
        pass


async def open_graph_pool():
    """Open the connection pool and set up checkpoint tables. Call from lifespan startup."""
    global tax_filing_graph
    checkpointer = create_postgres_checkpointer()
    if checkpointer is None or _graph_pool is None:
        return
    try:
        await _graph_pool.open(wait=True, timeout=10)
        await _graph_pool.check()   # validate all connections in pool on startup
        await checkpointer.setup()
        # Recompile the graph with the live postgres checkpointer
        workflow = StateGraph(TaxFilingState)
        workflow.add_node("interviewer", interviewer_node)
        workflow.add_node("research_and_calc", research_and_calc_node)
        workflow.add_node("auditor", auditor_node)
        workflow.set_entry_point("interviewer")
        workflow.add_conditional_edges(
            "interviewer", route_after_interviewer,
            {"interviewer": "interviewer", "researcher": "research_and_calc"},
        )
        workflow.add_edge("research_and_calc", "auditor")
        workflow.add_conditional_edges(
            "auditor", should_continue_to_end,
            {"researcher": "research_and_calc", "end": END},
        )
        tax_filing_graph = workflow.compile(checkpointer=checkpointer)
        print("[startup] LangGraph: AsyncPostgresSaver pool opened.")
    except Exception as e:
        print(f"[startup] LangGraph: falling back to InMemorySaver ({e})")


async def close_graph_pool():
    """Close the connection pool. Call from lifespan shutdown."""
    if _graph_pool is not None:
        try:
            await _graph_pool.close()
        except Exception:
            pass


# Initial graph uses InMemorySaver; open_graph_pool() upgrades it on startup
tax_filing_graph = create_tax_filing_graph()
