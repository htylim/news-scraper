"""Tests for the validation module."""

import pytest

from news_scraper.validation import (
    ValidationError,
    is_valid_slug,
    validate_slug,
)


class TestValidateSlug:
    """Tests for validate_slug function."""

    def test_valid_lowercase_slug(self) -> None:
        """Test valid lowercase slug passes."""
        assert validate_slug("infobae") == "infobae"

    def test_valid_slug_with_numbers(self) -> None:
        """Test slug with numbers passes."""
        assert validate_slug("news24") == "news24"

    def test_valid_slug_with_hyphen(self) -> None:
        """Test slug with hyphen passes."""
        assert validate_slug("la-nacion") == "la-nacion"

    def test_valid_slug_with_underscore(self) -> None:
        """Test slug with underscore passes."""
        assert validate_slug("la_nacion") == "la_nacion"

    def test_normalizes_to_lowercase(self) -> None:
        """Test uppercase is normalized to lowercase."""
        assert validate_slug("INFOBAE") == "infobae"
        assert validate_slug("LaNacion") == "lanacion"

    def test_empty_string_raises(self) -> None:
        """Test empty string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_raises(self) -> None:
        """Test string with whitespace raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("invalid source")

    def test_special_characters_raise(self) -> None:
        """Test special characters raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("source@name")
        with pytest.raises(ValidationError):
            validate_slug("source!name")
        with pytest.raises(ValidationError):
            validate_slug("source.name")

    def test_starting_with_hyphen_raises(self) -> None:
        """Test slug starting with hyphen raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("-invalid")

    def test_starting_with_underscore_raises(self) -> None:
        """Test slug starting with underscore raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("_invalid")

    def test_too_long_raises(self) -> None:
        """Test slug exceeding max length raises ValidationError."""
        long_slug = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            validate_slug(long_slug)
        assert "cannot exceed" in str(exc_info.value)

    def test_max_length_passes(self) -> None:
        """Test slug at max length passes."""
        max_slug = "a" * 100
        assert validate_slug(max_slug) == max_slug

    def test_custom_field_name_in_error(self) -> None:
        """Test custom field name appears in error message."""
        with pytest.raises(ValidationError) as exc_info:
            validate_slug("", field_name="source")
        assert "source" in str(exc_info.value)


class TestIsValidSlug:
    """Tests for is_valid_slug function."""

    def test_valid_slug_returns_true(self) -> None:
        """Test valid slug returns True."""
        assert is_valid_slug("infobae") is True
        assert is_valid_slug("la-nacion") is True
        assert is_valid_slug("news_24") is True

    def test_invalid_slug_returns_false(self) -> None:
        """Test invalid slug returns False."""
        assert is_valid_slug("") is False
        assert is_valid_slug("invalid source") is False
        assert is_valid_slug("-invalid") is False
