from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def test_engine():
    # StaticPool: all sessions share one connection, so `:memory:` is visible
    # to every session including those created in background tasks.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models import orm  # noqa: F401 — registers all ORM models
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_engine, db_session):
    """TestClient wired to an isolated in-memory SQLite DB.

    Both the FastAPI dependency (get_db) and the SessionLocal used directly
    in background tasks are patched to the same test session factory.
    """
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Patch SessionLocal imported at call-time inside background tasks so
    # they also use the in-memory DB rather than the file DB.
    with patch("app.database.SessionLocal", TestSession):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
