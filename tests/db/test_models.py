"""Tests for database models."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from news_scraper.db.models import Source


class TestSourceModel:
    """Tests for the Source model."""

    def test_create_source(self, db_session: Session) -> None:
        """Source can be created with required fields."""
        source = Source(name="testnews", url="https://test.com")
        db_session.add(source)
        db_session.commit()

        assert source.id is not None
        assert source.name == "testnews"
        assert source.url == "https://test.com"
        assert source.logo_url is None
        assert source.is_enabled is True

    def test_create_source_all_fields(self, db_session: Session) -> None:
        """Source can be created with all fields."""
        source = Source(
            name="fullnews",
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
        source = Source(name="timenews", url="https://time.com")
        db_session.add(source)
        db_session.commit()

        assert source.created_at is not None
        assert source.updated_at is not None

    def test_name_unique_constraint(self, db_session: Session) -> None:
        """Duplicate names are rejected."""
        source1 = Source(name="unique", url="https://one.com")
        db_session.add(source1)
        db_session.commit()

        source2 = Source(name="unique", url="https://two.com")
        db_session.add(source2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_url_unique_constraint(self, db_session: Session) -> None:
        """Duplicate URLs are rejected."""
        source1 = Source(name="first", url="https://same.com")
        db_session.add(source1)
        db_session.commit()

        source2 = Source(name="second", url="https://same.com")
        db_session.add(source2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_repr(self, db_session: Session) -> None:
        """__repr__ returns readable string."""
        source = Source(name="reprtest", url="https://repr.com")
        db_session.add(source)
        db_session.commit()

        assert "reprtest" in repr(source)
        assert str(source.id) in repr(source)

    def test_name_normalized_to_lowercase(self, db_session: Session) -> None:
        """Test name is normalized to lowercase on creation."""
        source = Source(name="INFOBAE", url="https://infobae.com")
        db_session.add(source)
        db_session.commit()

        assert source.name == "infobae"

    def test_name_with_valid_slug_chars(self, db_session: Session) -> None:
        """Test name with valid slug characters."""
        source = Source(name="la-nacion_24", url="https://lanacion.com")
        db_session.add(source)
        db_session.commit()

        assert source.name == "la-nacion_24"

    def test_name_with_spaces_raises(self) -> None:
        """Test name with spaces raises ValueError."""
        with pytest.raises(ValueError):
            Source(name="invalid source", url="https://invalid.com")

    def test_name_with_special_chars_raises(self) -> None:
        """Test name with special characters raises ValueError."""
        with pytest.raises(ValueError):
            Source(name="source@name", url="https://invalid.com")

    def test_empty_name_raises(self) -> None:
        """Test empty name raises ValueError."""
        with pytest.raises(ValueError):
            Source(name="", url="https://invalid.com")
