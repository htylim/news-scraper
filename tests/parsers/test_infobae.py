"""Tests for Infobae parser."""

from pathlib import Path

import pytest

from news_scraper.parsers.infobae import InfobaeParser


@pytest.fixture
def parser() -> InfobaeParser:
    """Create parser instance for tests."""
    return InfobaeParser()


class TestInfobaeParser:
    """Tests for InfobaeParser."""

    def test_parse_empty_html(self, parser: InfobaeParser) -> None:
        """Test parsing empty HTML returns empty list."""
        result = parser.parse("")
        assert result == []

    def test_parse_html_without_articles(self, parser: InfobaeParser) -> None:
        """Test parsing HTML with no article elements."""
        html = "<html><body><div>No articles here</div></body></html>"
        result = parser.parse(html)
        assert result == []

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
        assert result[0].position == 1

    def test_parse_multiple_story_cards(self, parser: InfobaeParser) -> None:
        """Test parsing HTML with multiple story cards."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/first-article/">
                <h2 class="story-card-hl">First Article</h2>
            </a>
            <a class="story-card-ctn" href="/second-article/">
                <h2 class="story-card-hl">Second Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 2
        assert result[0].headline == "First Article"
        assert result[0].position == 1
        assert result[1].headline == "Second Article"
        assert result[1].position == 2

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
        assert result[0].headline == "Main Headline"
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

    def test_parse_deduplicates_by_url(self, parser: InfobaeParser) -> None:
        """Test that duplicate URLs are filtered out, keeping first position."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/same-article/">
                <h2 class="story-card-hl">First Instance</h2>
            </a>
            <a class="story-card-ctn" href="/same-article/">
                <h2 class="story-card-hl">Second Instance</h2>
            </a>
            <a class="story-card-ctn" href="/different-article/">
                <h2 class="story-card-hl">Different Article</h2>
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        # Should only have 2 unique articles
        assert len(result) == 2
        # First article keeps position 1
        assert result[0].url == "https://www.infobae.com/same-article/"
        assert result[0].headline == "First Instance"
        assert result[0].position == 1
        # Different article gets position 2 (not 3)
        assert result[1].url == "https://www.infobae.com/different-article/"
        assert result[1].position == 2

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

        # External URL should be skipped
        assert len(result) == 1
        assert result[0].headline == "Valid Article"

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


class TestInfobaeParserHelpers:
    """Tests for InfobaeParser helper methods."""

    @pytest.fixture
    def parser(self) -> InfobaeParser:
        """Create parser instance for helper tests."""
        return InfobaeParser()

    def test_resolve_image_url_absolute(self, parser: InfobaeParser) -> None:
        """Test resolving absolute image URL."""
        url = "https://example.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == url

    def test_resolve_image_url_relative(self, parser: InfobaeParser) -> None:
        """Test resolving relative image URL."""
        url = "/images/photo.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://www.infobae.com/images/photo.jpg"

    def test_resolve_image_url_protocol_relative(self, parser: InfobaeParser) -> None:
        """Test resolving protocol-relative image URL."""
        url = "//cdn.example.com/image.jpg"
        result = parser._resolve_image_url(url)
        assert result == "https://cdn.example.com/image.jpg"

    def test_resolve_article_url_relative(self, parser: InfobaeParser) -> None:
        """Test resolving relative article URL."""
        result = parser._resolve_article_url("/article/path/")
        assert result == "https://www.infobae.com/article/path/"

    def test_resolve_article_url_absolute(self, parser: InfobaeParser) -> None:
        """Test resolving absolute article URL."""
        result = parser._resolve_article_url("https://www.infobae.com/article/")
        assert result == "https://www.infobae.com/article/"

    def test_resolve_article_url_external_rejected(self, parser: InfobaeParser) -> None:
        """Test that external URLs return None."""
        result = parser._resolve_article_url("https://other-site.com/article/")
        assert result is None

    def test_resolve_article_url_protocol_relative(self, parser: InfobaeParser) -> None:
        """Test resolving protocol-relative article URL."""
        result = parser._resolve_article_url("//www.infobae.com/article/")
        assert result == "https://www.infobae.com/article/"

    def test_resolve_article_url_without_www(self, parser: InfobaeParser) -> None:
        """Test resolving article URL without www prefix."""
        result = parser._resolve_article_url("https://infobae.com/article/")
        assert result == "https://infobae.com/article/"

    def test_extract_first_url_from_srcset_simple(self, parser: InfobaeParser) -> None:
        """Test extracting URL from simple srcset."""
        srcset = "https://example.com/image.jpg 1x"
        result = parser._extract_first_url_from_srcset(srcset)
        assert result == "https://example.com/image.jpg"

    def test_extract_first_url_from_srcset_multiple(
        self, parser: InfobaeParser
    ) -> None:
        """Test extracting first URL from srcset with multiple entries."""
        srcset = (
            "https://example.com/small.jpg 100w, https://example.com/large.jpg 200w"
        )
        result = parser._extract_first_url_from_srcset(srcset)
        assert result == "https://example.com/small.jpg"

    def test_extract_first_url_from_srcset_empty(self, parser: InfobaeParser) -> None:
        """Test extracting URL from empty srcset returns None."""
        result = parser._extract_first_url_from_srcset("")
        assert result is None

    def test_extract_first_url_from_srcset_whitespace(
        self, parser: InfobaeParser
    ) -> None:
        """Test extracting URL from whitespace-only srcset returns None."""
        result = parser._extract_first_url_from_srcset("   ")
        assert result is None

    def test_extract_first_url_from_srcset_url_only(
        self, parser: InfobaeParser
    ) -> None:
        """Test extracting URL from srcset without descriptor."""
        srcset = "https://example.com/image.jpg"
        result = parser._extract_first_url_from_srcset(srcset)
        assert result == "https://example.com/image.jpg"


class TestInfobaeParserLazyImages:
    """Tests for lazy-loaded image extraction."""

    @pytest.fixture
    def parser(self) -> InfobaeParser:
        """Create parser instance for tests."""
        return InfobaeParser()

    def test_parse_story_card_with_data_src(self, parser: InfobaeParser) -> None:
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

    def test_parse_story_card_with_data_srcset(self, parser: InfobaeParser) -> None:
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

    def test_parse_story_card_with_srcset(self, parser: InfobaeParser) -> None:
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

    def test_parse_story_card_data_src_priority_over_src(
        self, parser: InfobaeParser
    ) -> None:
        """Test that data-src takes priority over src for lazy-loaded images."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Priority Test</h2>
                <img class="story-card-img" data-src="https://example.com/real.jpg" src="https://example.com/placeholder.gif">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://example.com/real.jpg"

    def test_parse_story_card_falls_back_to_src(self, parser: InfobaeParser) -> None:
        """Test fallback to src when lazy-loading attributes not present."""
        html = """
        <html>
        <body>
            <a class="story-card-ctn" href="/article/">
                <h2 class="story-card-hl">Fallback Test</h2>
                <img class="story-card-img" src="https://example.com/direct.jpg">
            </a>
        </body>
        </html>
        """
        result = parser.parse(html)

        assert len(result) == 1
        assert result[0].image_url == "https://example.com/direct.jpg"


class TestInfobaeParserRealHtml:
    """Integration tests using real HTML fixture from Infobae."""

    @pytest.fixture
    def parser(self) -> InfobaeParser:
        """Create parser instance for tests."""
        return InfobaeParser()

    @pytest.fixture
    def infobae_html(self) -> str:
        """Load real Infobae HTML fixture."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "infobae_sample.html"
        return fixture_path.read_text()

    def test_parse_real_html_extracts_articles(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test parsing real Infobae HTML extracts expected articles."""
        result = parser.parse(infobae_html)

        # Fixture contains 5 articles
        assert len(result) == 5

    def test_parse_real_html_first_article(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test first article from real HTML has expected data."""
        result = parser.parse(infobae_html)

        first = result[0]
        assert "gobernadores" in first.headline.lower()
        assert first.url.startswith("https://www.infobae.com/")
        assert first.summary is not None  # First article has a deck
        assert first.image_url is not None
        assert first.image_url.startswith("https://")

    def test_parse_real_html_all_have_headlines(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test all parsed articles have headlines."""
        result = parser.parse(infobae_html)

        for article in result:
            assert article.headline
            assert len(article.headline) > 10

    def test_parse_real_html_all_have_urls(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test all parsed articles have valid URLs."""
        result = parser.parse(infobae_html)

        for article in result:
            assert article.url
            assert article.url.startswith("https://www.infobae.com/")

    def test_parse_real_html_some_have_images(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test at least one parsed article has an image URL.

        Images are optional per spec, so we only verify that image extraction
        works for articles that have images in the HTML.
        """
        result = parser.parse(infobae_html)

        articles_with_images = [a for a in result if a.image_url]
        assert len(articles_with_images) >= 1, (
            "Expected at least one article with an image"
        )

        for article in articles_with_images:
            assert article.image_url is not None
            assert article.image_url.startswith("https://")

    def test_parse_real_html_no_duplicates(
        self, parser: InfobaeParser, infobae_html: str
    ) -> None:
        """Test no duplicate URLs in parsed results."""
        result = parser.parse(infobae_html)

        urls = [article.url for article in result]
        assert len(urls) == len(set(urls))
