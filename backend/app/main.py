"""FastAPI main application for the Indian Tax Filing System."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine, Base
from app.api import auth, users, sdui, ws, documents, filing_v2, explain, behavior


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — ensure pgvector extension exists before create_all tries to
    # build the Vector(384) column on rag_documents. Safe no-op if already set.
    from sqlalchemy import text as _text
    with engine.begin() as _conn:
        _conn.execute(_text("CREATE EXTENSION IF NOT EXISTS vector;"))
    Base.metadata.create_all(bind=engine)
    from app.agents_v2.graph import open_graph_pool
    await open_graph_pool()
    print("Tax Filing System API starting up (Indian ITR-1 / FY2024-25)...")
    print("API documentation available at: http://localhost:8000/api/docs")
    print("Health check available at: http://localhost:8000/api/health")

    # Pre-warm the SentenceTransformer + DB pool in a background thread so the
    # first chat request doesn't pay the 5-10s cold-start cost.
    import asyncio as _aio

    async def _prewarm():
        try:
            from app.rag.retriever import get_retriever
            await _aio.to_thread(lambda: get_retriever().retrieve("warmup", k=1))
            print("[startup] RAG retriever warmed.")
        except Exception as e:
            print(f"[startup] RAG warmup skipped: {e}")

    _aio.create_task(_prewarm())

    yield
    # Shutdown
    from app.agents_v2.graph import close_graph_pool
    await close_graph_pool()
    print("Tax Filing System API shutting down...")


app = FastAPI(
    title="Indian Tax Filing System API",
    description="ITR-1 (Sahaj) filing system with deterministic tax engine and LangGraph agents",
    version="1.0.0-phase0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ============================================================================
# API Routers
# ============================================================================

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(sdui.router)
app.include_router(ws.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(filing_v2.router)  # Indian tax filing pipeline (LangGraph + tax_engine_in)
app.include_router(explain.router)    # XAI — /api/v2/explain endpoints
app.include_router(behavior.router)   # Adaptive engine — /api/users/behavior

# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================================
# Request Timing Middleware
# ============================================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to track request duration."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Surface Pydantic validation errors as 422.

    Pydantic v2 includes the original exception object in `ctx.error` for
    validator-raised errors. We run jsonable_encoder to drop non-serializable
    ValueError instances and then promote the first user-friendly message to
    the top level so the frontend can display it directly.
    """
    raw_errors = jsonable_encoder(exc.errors())
    first_msg = ""
    for err in raw_errors:
        if isinstance(err, dict) and err.get("msg"):
            first_msg = err["msg"]
            # Strip the "Value error, " prefix that Pydantic adds.
            if first_msg.startswith("Value error, "):
                first_msg = first_msg[len("Value error, "):]
            break
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": first_msg or "Validation error - please check your input",
            "errors": raw_errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "message": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc)
        }
    )
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": app.title,
        "version": app.version,
        "status": "running",
        "docs": "/api/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        - status: API status
        - database: Database connection status
        - timestamp: Current server time
    """
    from app.database import SessionLocal
    from datetime import datetime
    from sqlalchemy import text
    
    # Test database connection
    db_status = "healthy"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
