"""Tests for Infobae parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from news_scraper.parsers.sites.infobae import InfobaeParser


@pytest.fixture
def parser() -> InfobaeParser:
    """Create parser instance for tests."""
    return InfobaeParser()


class TestInfobaeParser:
    """Tests for InfobaeParser."""

    def test_parse_single_story_card(self, parser: InfobaeParser) -> None:
        """Test parsing HTML with a single story card."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/politica/2026/01/25/test-article/">
                <h2 class="story-card-hl">Test Headline</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Test Headline"
        assert (
            result[0].url == "https://www.infobae.com/politica/2026/01/25/test-article/"
        )

    def test_parse_story_card_with_deck(self, parser: InfobaeParser) -> None:
        """Test parsing story card with summary/deck."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article-with-deck/">
                <h2 class="story-card-hl">Main Headline</h2>
                <h3 class="story-card-deck">This is the summary of the article.</h3>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].summary == "This is the summary of the article."

    def test_parse_story_card_with_image(self, parser: InfobaeParser) -> None:
        """Test parsing story card with image."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article-image/">
                <h2 class="story-card-hl">Article with Image</h2>
                <img class="story-card-img" src="https://example.com/image.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://example.com/image.jpg"

    def test_parse_story_card_with_multiple_classes(
        self, parser: InfobaeParser
    ) -> None:
        """Test parsing story card where img has multiple CSS classes."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Test</h2>
                <img class="global-image story-card-img" src="https://example.com/image.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://example.com/image.jpg"

    def test_parse_skips_card_without_headline(self, parser: InfobaeParser) -> None:
        """Test that cards without headlines are skipped."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/no-headline/">
                <img class="story-card-img" src="image.jpg">
            </a>
            <a class="story-card-ctn" href="/valid-article/">
                <h2 class="story-card-hl">Valid Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_handles_absolute_urls(self, parser: InfobaeParser) -> None:
        """Test parsing handles absolute URLs correctly."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="https://www.infobae.com/full/path/article/">
                <h2 class="story-card-hl">Absolute URL Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.infobae.com/full/path/article/"

    def test_parse_skips_external_urls(self, parser: InfobaeParser) -> None:
        """Test that external URLs are rejected."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="https://other-site.com/article/">
                <h2 class="story-card-hl">External Article</h2>
            </a>
            <a class="story-card-ctn" href="/valid-article/">
                <h2 class="story-card-hl">Valid Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_strips_query_and_fragment(self, parser: InfobaeParser) -> None:
        """Test URL normalization strips query and fragment."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/?utm=1#frag">
                <h2 class="story-card-hl">Headline</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].url == "https://www.infobae.com/article/"

    def test_parse_resolves_relative_image_url(self, parser: InfobaeParser) -> None:
        """Test parsing resolves relative image URLs."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Test</h2>
                <img class="story-card-img" src="/images/photo.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://www.infobae.com/images/photo.jpg"

    def test_parse_resolves_protocol_relative_image_url(
        self, parser: InfobaeParser
    ) -> None:
        """Test parsing resolves protocol-relative image URLs."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Test</h2>
                <img class="story-card-img" src="//cdn.example.com/image.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://cdn.example.com/image.jpg"

    def test_parse_skips_card_without_href(self, parser: InfobaeParser) -> None:
        """Test that cards without href and no nested link are skipped."""
        html = """
        <html>
        <body>
            <div class="story-card-ctn">
                <h2 class="story-card-hl">No Link Article</h2>
            </div>
            <a class="story-card-ctn" href="/valid-article/">
                <h2 class="story-card-hl">Valid Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Valid Article"

    def test_parse_uses_nested_link_fallback(self, parser: InfobaeParser) -> None:
        """Test that nested <a href> is used when container has no href."""
        html = """
        <html>
        <body>
            <div class="story-card-ctn">
                <a href="/nested-link-article/">
                    <h2 class="story-card-hl">Nested Link Article</h2>
                </a>
            </div>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].headline == "Nested Link Article"
        assert result[0].url == "https://www.infobae.com/nested-link-article/"

    def test_parse_lazy_image_data_src(self, parser: InfobaeParser) -> None:
        """Test parsing story card with lazy-loaded image using data-src."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Lazy Image Test</h2>
                <img class="story-card-img"
                     data-src="https://ex.co/lazy.jpg" src="placeholder.gif">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://ex.co/lazy.jpg"

    def test_parse_lazy_image_data_srcset(self, parser: InfobaeParser) -> None:
        """Test parsing story card with lazy-loaded responsive image."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Lazy Srcset Test</h2>
                <img class="story-card-img"
                     data-srcset="https://ex.co/s.jpg 100w, https://ex.co/l.jpg 200w">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://ex.co/s.jpg"

    def test_parse_lazy_image_srcset(self, parser: InfobaeParser) -> None:
        """Test parsing story card with standard responsive image."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Srcset Test</h2>
                <img class="story-card-img"
                     srcset="https://ex.co/1x.jpg 1x, https://ex.co/2x.jpg 2x">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://ex.co/1x.jpg"


class TestInfobaeParserRealHtml:
    """Integration tests using real HTML fixture from Infobae."""

    @pytest.fixture
    def parser(self) -> InfobaeParser:
        """Create parser instance for tests."""
        return InfobaeParser()

    @pytest.fixture
    def infobae_html(self) -> str:
        """Load real Infobae HTML fixture."""
        fixture_path = Path(__file__).parents[2] / "fixtures" / "infobae_sample.html"
        return fixture_path.read_text(encoding="utf-8")

    def test_parse_real_html_extracts_articles(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test parsing real Infobae HTML extracts articles."""
        result = parser.parse(infobae_html)
        assert len(result) > 0

    def test_parse_real_html_first_article_has_fields(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(infobae_html)
        first = result[0]

        assert first.headline
        assert first.url.startswith("https://www.infobae.com/")
