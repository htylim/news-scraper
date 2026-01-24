"""Tests for database models."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from news_scraper.db.models import Source


class TestSourceModel:
    """Tests for the Source model."""

    def test_create_source(self, db_session: Session) -> None:
        """Source can be created with required fields."""
        source = Source(name="Test News", url="https://test.com")
        db_session.add(source)
        db_session.commit()

        assert source.id is not None
        assert source.name == "Test News"
        assert source.url == "https://test.com"
        assert source.logo_url is None
        assert source.is_enabled is True

    def test_create_source_all_fields(self, db_session: Session) -> None:
        """Source can be created with all fields."""
        source = Source(
            name="Full News",
            url="https://full.com",
            logo_url="https://full.com/logo.png",
            is_enabled=False,
        )
        db_session.add(source)
        db_session.commit()

        assert source.logo_url == "https://full.com/logo.png"
        assert source.is_enabled is False

    def test_timestamps_set_on_create(self, db_session: Session) -> None:
        """created_at and updated_at are set on insert."""
        source = Source(name="Time News", url="https://time.com")
        db_session.add(source)
        db_session.commit()

        assert source.created_at is not None
        assert source.updated_at is not None

    def test_name_unique_constraint(self, db_session: Session) -> None:
        """Duplicate names are rejected."""
        source1 = Source(name="Unique", url="https://one.com")
        db_session.add(source1)
        db_session.commit()

        source2 = Source(name="Unique", url="https://two.com")
        db_session.add(source2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_url_unique_constraint(self, db_session: Session) -> None:
        """Duplicate URLs are rejected."""
        source1 = Source(name="First", url="https://same.com")
        db_session.add(source1)
        db_session.commit()

        source2 = Source(name="Second", url="https://same.com")
        db_session.add(source2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_repr(self, db_session: Session) -> None:
        """__repr__ returns readable string."""
        source = Source(name="Repr Test", url="https://repr.com")
        db_session.add(source)
        db_session.commit()

        assert "Repr Test" in repr(source)
        assert str(source.id) in repr(source)
