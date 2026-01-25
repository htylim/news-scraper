"""Tests for parser base classes."""

import pytest

from news_scraper.parsers.base import Article


class TestArticle:
    """Tests for Article dataclass."""

    def test_article_with_all_fields(self) -> None:
        """Test creating article with all fields."""
        article = Article(
            headline="Test Headline",
            url="https://example.com/article",
            summary="Test summary",
            image_url="https://example.com/image.jpg",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.summary == "Test summary"
        assert article.image_url == "https://example.com/image.jpg"

    def test_article_with_required_fields_only(self) -> None:
        """Test creating article with only required fields."""
        article = Article(
            headline="Test Headline",
            url="https://example.com/article",
        )

        assert article.headline == "Test Headline"
        assert article.url == "https://example.com/article"
        assert article.summary is None
        assert article.image_url is None

    def test_article_is_frozen(self) -> None:
        """Test that Article is immutable."""
        article = Article(headline="Test", url="https://example.com")

        with pytest.raises(AttributeError):
            article.headline = "Modified"  # type: ignore[misc]

    def test_article_is_hashable(self) -> None:
        """Test that Article can be used in sets."""
        article1 = Article(headline="Test", url="https://example.com")
        article2 = Article(headline="Test", url="https://example.com")

        article_set = {article1, article2}
        assert len(article_set) == 1
