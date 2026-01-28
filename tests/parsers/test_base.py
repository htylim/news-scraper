"""Tests for parser base classes."""

import pytest

from news_scraper.parsers.base import ParsedArticle


class TestParsedArticle:
    """Tests for ParsedArticle dataclass."""

    def test_article_with_all_fields(self) -> None:
        """Test creating article with all fields."""
        article = ParsedArticle(
            headline="Test Headline",
            url="https://example.com/article",
            position=1,
            summary="Test summary",
            image_url="https://example.com/image.jpg",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.position == 1
        assert article.summary == "Test summary"
        assert article.image_url == "https://example.com/image.jpg"

    def test_article_with_required_fields_only(self) -> None:
        """Test creating article with only required fields."""
        article = ParsedArticle(
            headline="Test Headline",
            url="https://example.com/article",
            position=5,
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.position == 5
        assert article.summary is None
        assert article.image_url is None

    def test_article_is_frozen(self) -> None:
        """Test that ParsedArticle is immutable."""
        article = ParsedArticle(headline="Test", url="https://example.com", position=1)

        with pytest.raises(AttributeError):
            article.headline = "Modified"  # type: ignore[misc]

    def test_article_is_hashable(self) -> None:
        """Test that ParsedArticle can be used in sets."""
        article1 = ParsedArticle(headline="Test", url="https://example.com", position=1)
        article2 = ParsedArticle(headline="Test", url="https://example.com", position=1)

        article_set = {article1, article2}
        assert len(article_set) == 1
