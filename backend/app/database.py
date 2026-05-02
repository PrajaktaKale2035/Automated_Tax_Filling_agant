"""Database configuration and session management."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://taxagent:taxagent_secure_password_2024@localhost:5436/tax_filing_db")

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Maximum number of connections that can be created beyond pool_size
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=os.getenv("DEBUG", "false").lower() == "true",  # Log SQL statements in debug mode
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Create Base class for models (SQLAlchemy 2.0 style)
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    
    Usage in FastAPI:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models here to ensure they are registered with Base
    from app import models  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def check_db_connection():
    """
    Check database connection health.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
