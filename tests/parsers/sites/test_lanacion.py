"""Tests for La Nacion parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from news_scraper.parsers.sites.lanacion import LaNacionParser


@pytest.fixture
def parser() -> LaNacionParser:
    """Create parser instance for tests."""
    return LaNacionParser()


class TestLaNacionParser:
    """Tests for LaNacionParser."""

    def test_parse_single_article_with_h1(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with a single featured article (h1 headline)."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/politica/test-article-nid123/">
                    <h1>Test Headline</h1>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Test Headline"
        assert (
            result[0].url == "https://www.lanacion.com.ar/politica/test-article-nid123/"
        )

    def test_parse_single_article_with_h2(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with a regular article (h2 headline)."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/economia/test-nid456/">
                    <h2>Economic News Headline</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Economic News Headline"

    def test_parse_article_with_h1_headline_and_h2_summary(
        self, parser: LaNacionParser
    ) -> None:
        """Test parsing article with h1 headline and h2 summary."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <h1>Main Headline</h1>
                    <h2>This is the summary text.</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Main Headline"
        assert result[0].summary == "This is the summary text."

    def test_parse_article_with_h2_headline_and_h3_summary(
        self, parser: LaNacionParser
    ) -> None:
        """Test parsing article with h2 headline and h3 summary."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <h2>Regular Headline</h2>
                    <h3>Brief description of the article.</h3>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Regular Headline"
        assert result[0].summary == "Brief description of the article."

    def test_parse_headline_preserves_space_between_span_and_sibling_text(
        self, parser: LaNacionParser
    ) -> None:
        """Headline span+sibling keeps space (get_text(strip=True) drops it)."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <h2><span class="lead">"X". </span>La Anmat prohibió</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)
        assert len(result) == 1
        assert result[0].headline == '"X". La Anmat prohibió'

    def test_parse_article_with_image(self, parser: LaNacionParser) -> None:
        """Test parsing article with image."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/">
                    <picture>
                        <img src="https://www.lanacion.com.ar/resizer/image.jpg"
                             alt="Image description">
                    </picture>
                    <h2>Article with Image</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://www.lanacion.com.ar/resizer/image.jpg"

    def test_parse_skips_card_without_headline(self, parser: LaNacionParser) -> None:
        """Test that cards without headlines are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/no-headline/">
                    <img src="image.jpg">
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid-article/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_skips_card_without_url(self, parser: LaNacionParser) -> None:
        """Test that cards without URLs are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <h2>No Link Article</h2>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_handles_absolute_urls(self, parser: LaNacionParser) -> None:
        """Test parsing handles absolute URLs correctly."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="https://www.lanacion.com.ar/full/path/">
                    <h2>Absolute URL Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.lanacion.com.ar/full/path/"

    def test_parse_skips_external_urls(self, parser: LaNacionParser) -> None:
        """Test that external URLs are rejected."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="https://other-site.com/article/">
                    <h2>External Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid-article/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_accepts_lanacion_without_www(self, parser: LaNacionParser) -> None:
        """Test that lanacion.com.ar without www is accepted."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="https://lanacion.com.ar/article/">
                    <h2>No WWW Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://lanacion.com.ar/article/"

    def test_parse_skips_fragment_only_href(self, parser: LaNacionParser) -> None:
        """Test that articles with fragment-only href are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="#">
                    <h2>Fragment Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="#section">
                    <h2>Section Fragment Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid-article/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_skips_root_path_href(self, parser: LaNacionParser) -> None:
        """Test that articles with root path href are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/">
                    <h2>Homepage Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/valid-article/">
                    <h2>Valid Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_normalizes_urls_with_query_params(
        self, parser: LaNacionParser
    ) -> None:
        """Test that URLs with tracking params are normalized."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/?utm_source=home#top">
                    <h2>First Instance</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.lanacion.com.ar/article/"


class TestLaNacionParserRealHtml:
    """Integration tests using real HTML fixture from La Nacion."""

    @pytest.fixture
    def parser(self) -> LaNacionParser:
        """Create parser instance for tests."""
        return LaNacionParser()

    @pytest.fixture
    def lanacion_html(self) -> str:
        """Load real La Nacion HTML fixture."""
        fixture_path = Path(__file__).parents[2] / "fixtures" / "lanacion_sample.html"
        return fixture_path.read_text(encoding="utf-8")

    def test_parse_real_html_extracts_articles(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test parsing real La Nacion HTML extracts articles."""
        result = parser.parse(lanacion_html)
        assert len(result) > 0

    def test_parse_real_html_first_article_has_fields(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(lanacion_html)
        first = result[0]

        assert first.headline
        assert first.url.startswith("https://www.lanacion.com.ar/")
