"""Tests for La Nacion parser."""

from pathlib import Path

import pytest

from news_scraper.parsers.lanacion import LaNacionParser


@pytest.fixture
def parser() -> LaNacionParser:
    """Create parser instance for tests."""
    return LaNacionParser()


class TestLaNacionParser:
    """Tests for LaNacionParser."""

    def test_parse_empty_html(self, parser: LaNacionParser) -> None:
        """Test parsing empty HTML returns empty list."""
        result = parser.parse("")
        assert result == []

    def test_parse_html_without_articles(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with no article elements."""
        html = "<html><body><div>No articles here</div></body></html>"
        result = parser.parse(html)
        assert result == []

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
        assert result[0].position == 1

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
        assert result[0].position == 1

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

    def test_parse_multiple_articles(self, parser: LaNacionParser) -> None:
        """Test parsing HTML with multiple articles."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/first/">
                    <h2>First Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/second/">
                    <h2>Second Article</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/third/">
                    <h2>Third Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 3
        assert result[0].headline == "First Article"
        assert result[0].position == 1
        assert result[1].headline == "Second Article"
        assert result[1].position == 2
        assert result[2].headline == "Third Article"
        assert result[2].position == 3

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

    def test_parse_deduplicates_by_url(self, parser: LaNacionParser) -> None:
        """Test that duplicate URLs are filtered out."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/same-article/">
                    <h2>First Instance</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/same-article/">
                    <h2>Second Instance</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/different-article/">
                    <h2>Different Article</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        # Should only have 2 unique articles
        assert len(result) == 2
        assert result[0].headline == "First Instance"
        assert result[0].position == 1
        assert result[1].headline == "Different Article"
        assert result[1].position == 2

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

        # External URL should be skipped
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

    def test_parse_skips_empty_href(self, parser: LaNacionParser) -> None:
        """Test that articles with empty href are skipped."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="">
                    <h2>Empty Href Article</h2>
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
        """Test that URLs with tracking params are normalized for deduplication."""
        html = """
        <html>
        <body>
            <article class="ln-card">
                <a class="link ln-link" href="/article/?utm_source=home">
                    <h2>First Instance</h2>
                </a>
            </article>
            <article class="ln-card">
                <a class="link ln-link" href="/article/?ref=sidebar">
                    <h2>Second Instance</h2>
                </a>
            </article>
        </body>
        </html>
        """
        result = parser.parse(html)

        # Both should normalize to same URL, only first kept
        assert len(result) == 1
        assert result[0].headline == "First Instance"
        assert result[0].url == "https://www.lanacion.com.ar/article/"


class TestLaNacionParserHelpers:
    """Tests for LaNacionParser helper methods."""

    @pytest.fixture
    def parser(self) -> LaNacionParser:
        """Create parser instance for helper tests."""
        return LaNacionParser()

    def test_resolve_image_url_absolute(self, parser: LaNacionParser) -> None:
        """Test resolving absolute image URL."""
        url = "https://cdn.lanacion.com.ar/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == url

    def test_resolve_image_url_relative(self, parser: LaNacionParser) -> None:
        """Test resolving relative image URL."""
        url = "/images/photo.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://www.lanacion.com.ar/images/photo.jpg"

    def test_resolve_image_url_protocol_relative(self, parser: LaNacionParser) -> None:
        """Test resolving protocol-relative image URL."""
        url = "//cdn.lanacion.com.ar/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://cdn.lanacion.com.ar/image.jpg"

    def test_resolve_article_url_relative(self, parser: LaNacionParser) -> None:
        """Test resolving relative article URL."""
        result = parser._resolve_article_url("/politica/article-nid123/")
        assert result == "https://www.lanacion.com.ar/politica/article-nid123/"

    def test_resolve_article_url_absolute(self, parser: LaNacionParser) -> None:
        """Test resolving absolute article URL."""
        result = parser._resolve_article_url("https://www.lanacion.com.ar/article/")
        assert result == "https://www.lanacion.com.ar/article/"

    def test_resolve_article_url_external_rejected(
        self, parser: LaNacionParser
    ) -> None:
        """Test that external URLs return None."""
        result = parser._resolve_article_url("https://other-site.com/article/")
        assert result is None

    def test_resolve_article_url_empty_rejected(self, parser: LaNacionParser) -> None:
        """Test that empty hrefs return None."""
        assert parser._resolve_article_url("") is None
        assert parser._resolve_article_url("   ") is None

    def test_resolve_article_url_fragment_only_rejected(
        self, parser: LaNacionParser
    ) -> None:
        """Test that fragment-only hrefs return None."""
        assert parser._resolve_article_url("#") is None
        assert parser._resolve_article_url("#section") is None
        assert parser._resolve_article_url("#top") is None

    def test_resolve_article_url_root_path_rejected(
        self, parser: LaNacionParser
    ) -> None:
        """Test that root path (homepage) is rejected."""
        assert parser._resolve_article_url("/") is None
        assert parser._resolve_article_url("https://www.lanacion.com.ar/") is None
        assert parser._resolve_article_url("https://www.lanacion.com.ar") is None

    def test_normalize_url_strips_all_query_params(
        self, parser: LaNacionParser
    ) -> None:
        """Test that normalization strips all query params."""
        url = "https://www.lanacion.com.ar/article/?utm_source=x&ref=home&source=feed"
        result = parser._normalize_url(url)
        assert result == "https://www.lanacion.com.ar/article/"

    def test_normalize_url_strips_fragment(self, parser: LaNacionParser) -> None:
        """Test that normalization strips fragments."""
        url = "https://www.lanacion.com.ar/article/#comments"
        result = parser._normalize_url(url)
        assert result == "https://www.lanacion.com.ar/article/"


class TestLaNacionParserRealHtml:
    """Integration tests using real HTML fixture from La Nacion."""

    # Fixture-based expectations: update these constants only when regenerating
    # the fixture. This keeps tests deterministic and avoids brittle ratio checks.

    EXPECTED_ARTICLE_COUNT = 128
    EXPECTED_SUMMARY_COUNT = 10
    EXPECTED_WITH_IMAGES_COUNT = 122

    @pytest.fixture
    def parser(self) -> LaNacionParser:
        """Create parser instance for tests."""
        return LaNacionParser()

    @pytest.fixture
    def lanacion_html(self) -> str:
        """Load real La Nacion HTML fixture."""
        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "lanacion_sample.html"
        )
        return fixture_path.read_text(encoding="utf-8")

    def test_parse_real_html_extracts_articles(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test parsing real La Nacion HTML extracts expected articles."""
        result = parser.parse(lanacion_html)

        # Fixture-based expectation: update constants when fixture changes
        assert len(result) == self.EXPECTED_ARTICLE_COUNT

    def test_parse_real_html_first_article(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(lanacion_html)

        first = result[0]
        assert first.headline  # Has headline
        assert len(first.headline) > 10  # Non-trivial headline
        assert first.url.startswith("https://www.lanacion.com.ar/")
        assert first.position == 1
        assert first.image_url is not None
        assert first.image_url.startswith("https://")

    def test_parse_real_html_all_have_headlines(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test all parsed articles have headlines."""
        result = parser.parse(lanacion_html)

        for article in result:
            assert article.headline
            assert len(article.headline) > 5

    def test_parse_real_html_all_have_urls(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test all parsed articles have valid URLs."""
        result = parser.parse(lanacion_html)

        for article in result:
            assert article.url
            assert article.url.startswith("https://")
            assert "lanacion.com.ar" in article.url

    def test_parse_real_html_no_duplicates(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test no duplicate URLs in parsed results."""
        result = parser.parse(lanacion_html)

        urls = [article.url for article in result]
        assert len(urls) == len(set(urls))

    def test_parse_real_html_positions_sequential(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test positions are sequential starting from 1."""
        result = parser.parse(lanacion_html)

        positions = [article.position for article in result]
        expected = list(range(1, len(result) + 1))
        assert positions == expected

    def test_parse_real_html_some_have_summaries(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test some articles have summaries."""
        result = parser.parse(lanacion_html)

        summaries = [a.summary for a in result if a.summary]
        assert len(summaries) == self.EXPECTED_SUMMARY_COUNT

    def test_parse_real_html_most_have_images(
        self, parser: LaNacionParser, lanacion_html: str
    ) -> None:
        """Test most articles have images."""
        result = parser.parse(lanacion_html)

        with_images = [a for a in result if a.image_url]
        assert len(with_images) == self.EXPECTED_WITH_IMAGES_COUNT
