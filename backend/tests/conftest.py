"""Shared pytest fixtures for the Indian Tax Filing test suite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


@pytest.fixture(scope="function")
def db_session():
    """Per-test isolated SQLite DB.

    Uses StaticPool so the in-memory DB is shared across all connections from
    the same engine (otherwise FastAPI's dependency-injected session would
    open a new connection seeing an empty schema).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
