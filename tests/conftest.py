"""Shared test fixtures."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from news_scraper.db.base import Base
from news_scraper.db.models import Source  # noqa: F401 - registers model


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """In-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
