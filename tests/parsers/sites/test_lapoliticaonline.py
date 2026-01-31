"""Tests for La Política Online parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from news_scraper.parsers.sites.lapoliticaonline import LaPoliticaOnlineParser


@pytest.fixture
def parser() -> LaPoliticaOnlineParser:
    """Create parser instance for tests."""
    return LaPoliticaOnlineParser()


class TestLaPoliticaOnlineParser:
    """Tests for LaPoliticaOnlineParser."""

    def test_parse_empty_html(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing empty HTML returns empty list."""
        result = parser.parse("")
        assert result == []

    def test_parse_html_without_articles(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing HTML with no article elements."""
        html = "<html><body><div>No articles here</div></body></html>"
        result = parser.parse(html)
        assert result == []

    def test_parse_single_article(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing HTML with a single article."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="/politica/test-article-123/">Test Headline</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Test Headline"
        assert (
            result[0].url
            == "https://www.lapoliticaonline.com/politica/test-article-123/"
        )
        assert result[0].position == 1

    def test_parse_multiple_articles(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing HTML with multiple articles."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="/first/">First Article</a>
            </h2>
            <h2 class="title">
                <a href="/second/">Second Article</a>
            </h2>
            <h2 class="title">
                <a href="/third/">Third Article</a>
            </h2>
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

    def test_parse_article_with_image(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing article with image."""
        html = """
        <html>
        <body>
            <div class="noticia">
                <img src="/files/image/test.jpg" />
                <h2 class="title">
                    <a href="/article/">Article with Image</a>
                </h2>
            </div>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert (
            result[0].image_url
            == "https://www.lapoliticaonline.com/files/image/test.jpg"
        )

    def test_parse_images_scoped_to_article_item(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that image lookup is scoped to the article item."""
        html = """
        <html>
        <body>
            <div class="noticia">
                <div class="items">
                    <div class="item">
                        <div class="image">
                            <a href="/first/">
                                <img src="/files/image/first.jpg" />
                            </a>
                        </div>
                        <h2 class="title">
                            <a href="/first/">First Article</a>
                        </h2>
                    </div>
                    <div class="item">
                        <div class="image">
                            <a href="/second/">
                                <img src="/files/image/second.jpg" />
                            </a>
                        </div>
                        <h2 class="title">
                            <a href="/second/">Second Article</a>
                        </h2>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 2
        assert result[0].headline == "First Article"
        assert (
            result[0].image_url
            == "https://www.lapoliticaonline.com/files/image/first.jpg"
        )
        assert result[1].headline == "Second Article"
        assert (
            result[1].image_url
            == "https://www.lapoliticaonline.com/files/image/second.jpg"
        )

    def test_parse_skips_data_uri_images(self, parser: LaPoliticaOnlineParser) -> None:
        """Test that data URI images are skipped."""
        html = """
        <html>
        <body>
            <div class="noticia">
                <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." />
                <h2 class="title">
                    <a href="/article/">Article</a>
                </h2>
            </div>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url is None

    def test_parse_deduplicates_by_url(self, parser: LaPoliticaOnlineParser) -> None:
        """Test that duplicate URLs are filtered out."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="/same-article/">First Instance</a>
            </h2>
            <h2 class="title">
                <a href="/same-article/">Second Instance</a>
            </h2>
            <h2 class="title">
                <a href="/different-article/">Different Article</a>
            </h2>
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

    def test_parse_skips_title_without_link(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that titles without links are skipped."""
        html = """
        <html>
        <body>
            <h2 class="title">No Link Title</h2>
            <h2 class="title">
                <a href="/valid-article/">Valid Article</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_handles_absolute_urls(self, parser: LaPoliticaOnlineParser) -> None:
        """Test parsing handles absolute URLs correctly."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="https://www.lapoliticaonline.com/full/path/">
                    Absolute URL Article
                </a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.lapoliticaonline.com/full/path/"

    def test_parse_skips_external_urls(self, parser: LaPoliticaOnlineParser) -> None:
        """Test that external URLs are rejected."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="https://other-site.com/article/">External Article</a>
            </h2>
            <h2 class="title">
                <a href="/valid-article/">Valid Article</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        # External URL should be skipped
        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_accepts_lapoliticaonline_without_www(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test that lapoliticaonline.com without www is accepted."""
        html = """
        <html>
        <body>
            <h2 class="title">
                <a href="https://lapoliticaonline.com/article/">No WWW Article</a>
            </h2>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://lapoliticaonline.com/article/"


class TestLaPoliticaOnlineParserHelpers:
    """Tests for LaPoliticaOnlineParser helper methods."""

    @pytest.fixture
    def parser(self) -> LaPoliticaOnlineParser:
        """Create parser instance for helper tests."""
        return LaPoliticaOnlineParser()

    def test_resolve_image_url_absolute(self, parser: LaPoliticaOnlineParser) -> None:
        """Test resolving absolute image URL."""
        url = "https://cdn.lapoliticaonline.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == url

    def test_resolve_image_url_relative(self, parser: LaPoliticaOnlineParser) -> None:
        """Test resolving relative image URL."""
        url = "/files/image/photo.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://www.lapoliticaonline.com/files/image/photo.jpg"

    def test_resolve_image_url_protocol_relative(
        self, parser: LaPoliticaOnlineParser
    ) -> None:
        """Test resolving protocol-relative image URL."""
        url = "//cdn.lapoliticaonline.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://cdn.lapoliticaonline.com/image.jpg"


class TestLaPoliticaOnlineParserRealHtml:
    """Integration tests using real HTML fixture from La Política Online."""

    # Fixture-based expectations: update these constants only when regenerating
    # the fixture. This keeps tests deterministic and avoids brittle ratio checks.

    EXPECTED_ARTICLE_COUNT = 90  # Update to match fixture snapshot
    EXPECTED_WITH_IMAGES_COUNT = 11  # Update to match fixture snapshot

    @pytest.fixture
    def parser(self) -> LaPoliticaOnlineParser:
        """Create parser instance for tests."""
        return LaPoliticaOnlineParser()

    @pytest.fixture
    def lapoliticaonline_html(self) -> str:
        """Load real La Política Online HTML fixture."""
        fixture_path = (
            Path(__file__).parent.parent.parent
            / "fixtures"
            / "lapoliticaonline_sample.html"
        )
        return fixture_path.read_text(encoding="utf-8")

    def test_parse_real_html_extracts_articles(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test parsing real La Política Online HTML extracts expected articles."""
        result = parser.parse(lapoliticaonline_html)

        # Fixture-based expectation: update constants when fixture changes
        assert len(result) == self.EXPECTED_ARTICLE_COUNT

    def test_parse_real_html_first_article(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(lapoliticaonline_html)

        if not result:
            pytest.skip("No articles found in fixture")

        first = result[0]
        assert first.headline  # Has headline
        assert len(first.headline) > 10  # Non-trivial headline
        assert first.url.startswith("https://www.lapoliticaonline.com/")
        assert first.position == 1

    def test_parse_real_html_all_have_headlines(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test all parsed articles have headlines."""
        result = parser.parse(lapoliticaonline_html)

        for article in result:
            assert article.headline
            assert len(article.headline) > 5

    def test_parse_real_html_all_have_urls(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test all parsed articles have valid URLs."""
        result = parser.parse(lapoliticaonline_html)

        for article in result:
            assert article.url
            assert article.url.startswith("https://")
            assert "lapoliticaonline.com" in article.url

    def test_parse_real_html_no_duplicates(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test no duplicate URLs in parsed results."""
        result = parser.parse(lapoliticaonline_html)

        urls = [article.url for article in result]
        assert len(urls) == len(set(urls))

    def test_parse_real_html_positions_sequential(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test positions are sequential starting from 1."""
        result = parser.parse(lapoliticaonline_html)

        positions = [article.position for article in result]
        expected = list(range(1, len(result) + 1))
        assert positions == expected

    def test_parse_real_html_image_count_matches_fixture(
        self, parser: LaPoliticaOnlineParser, lapoliticaonline_html: str
    ) -> None:
        """Test image count matches fixture snapshot."""
        result = parser.parse(lapoliticaonline_html)

        with_images = [a for a in result if a.image_url]
        assert len(with_images) == self.EXPECTED_WITH_IMAGES_COUNT
