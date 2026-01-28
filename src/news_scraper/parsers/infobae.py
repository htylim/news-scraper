"""Parser for Infobae news site."""

from typing import TypedDict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from news_scraper.logging import get_logger
from news_scraper.parsers.base import ParsedArticle


class _ParsedData(TypedDict):
    """Internal type for parsed article data before creating ParsedArticle."""

    headline: str
    url: str
    summary: str | None
    image_url: str | None


# Base URL for resolving relative links
BASE_URL = "https://www.infobae.com"


class InfobaeParser:
    """Parser for Infobae front page HTML.

    Extracts articles from Infobae's HTML structure. Articles are identified
    by elements with class "story-card-ctn".
    """

    def parse(self, html: str) -> list[ParsedArticle]:
        """Parse Infobae HTML and extract articles.

        Extracts ALL articles found on the page, deduplicates by URL
        (keeping first occurrence), assigns positions, and logs errors
        for individual articles that fail to parse.

        Args:
            html: Raw HTML content from Infobae's front page.

        Returns:
            List of unique ParsedArticle objects with positions.
            Empty list if no articles found.
        """
        log = get_logger()
        soup = BeautifulSoup(html, "lxml")
        articles: list[ParsedArticle] = []
        seen_urls: set[str] = set()
        position = 0  # Will be incremented before use (1-based)

        # Find all story card containers
        article_elements = soup.find_all(class_="story-card-ctn")

        for element in article_elements:
            if not isinstance(element, Tag):
                continue

            try:
                parsed = self._parse_article_element(element)
                if parsed and parsed["url"] not in seen_urls:
                    position += 1
                    articles.append(
                        ParsedArticle(
                            headline=parsed["headline"],
                            url=parsed["url"],
                            position=position,
                            summary=parsed.get("summary"),
                            image_url=parsed.get("image_url"),
                        )
                    )
                    seen_urls.add(parsed["url"])
            except Exception:
                # Log error with stack trace and continue with next article
                log.exception("Failed to parse article element")
                continue

        return articles

    def _parse_article_element(self, element: Tag) -> _ParsedData | None:
        """Extract article data from a story-card-ctn element.

        Args:
            element: BeautifulSoup Tag containing article data.

        Returns:
            Dict with article fields if extraction successful, None otherwise.
        """
        headline = self._extract_headline(element)
        url = self._extract_url(element)

        # Headline and URL are required
        if not headline or not url:
            return None

        summary = self._extract_summary(element)
        image_url = self._extract_image_url(element)

        return {
            "headline": headline,
            "url": url,
            "summary": summary,
            "image_url": image_url,
        }

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from article element.

        Args:
            element: Article container Tag.

        Returns:
            Headline text or None if not found.
        """
        # Primary: Look for h2 with story-card-hl class
        h2 = element.find("h2", class_="story-card-hl")
        if h2:
            text: str = h2.get_text(strip=True)
            if text:
                return text

        # Fallback: any h2 (but not h3, which may be a deck/summary)
        h2_fallback = element.find("h2")
        if h2_fallback:
            text = h2_fallback.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element.

        Only accepts URLs from the same domain (relative or absolute to BASE_URL).
        External or unexpected URLs are logged and skipped.

        Args:
            element: Article container Tag.

        Returns:
            Absolute URL or None if not found or rejected.
        """
        log = get_logger()

        # The story-card-ctn is an <a> tag itself with href
        href = element.get("href")
        if href and isinstance(href, str):
            resolved = self._resolve_article_url(href)
            if resolved:
                return resolved
            log.debug("Rejected URL from href attribute", href=href)

        # Fallback: find nested link
        link = element.find("a", href=True)
        if link:
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = self._resolve_article_url(href)
                if resolved:
                    return resolved
                log.debug("Rejected URL from nested link", href=href)

        return None

    def _resolve_article_url(self, href: str) -> str | None:
        """Resolve href to absolute URL if it's from the same domain.

        Args:
            href: URL string (relative or absolute).

        Returns:
            Absolute URL if valid, None if external/rejected.
        """
        # Allowlist of valid Infobae hostnames
        allowed_hosts = {"www.infobae.com", "infobae.com"}

        # Use urljoin to resolve relative and protocol-relative URLs
        resolved = urljoin(BASE_URL, href)
        parsed = urlparse(resolved)

        # Check if the resolved URL is from an allowed host
        if parsed.netloc in allowed_hosts:
            return resolved
        return None

    def _extract_summary(self, element: Tag) -> str | None:
        """Extract summary/deck from article element.

        Args:
            element: Article container Tag.

        Returns:
            Summary text or None if not found.
        """
        # Look for h3 with story-card-deck class
        deck = element.find("h3", class_="story-card-deck")
        if deck:
            text: str = deck.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element.

        Checks multiple attributes to handle lazy-loaded images:
        - data-src: Common lazy-loading attribute
        - data-srcset: Lazy-loaded responsive images
        - srcset: Standard responsive images (picks first URL)
        - src: Standard image source (fallback)

        Args:
            element: Article container Tag.

        Returns:
            Absolute image URL or None if not found.
        """
        # Look for img with story-card-img class (partial match, may have other classes)
        img = element.find("img", class_="story-card-img")
        if not img:
            # Fallback: any img in the element
            img = element.find("img")

        if img and isinstance(img, Tag):
            # Check lazy-loading attributes first, then fall back to src
            # Priority: data-src > data-srcset > srcset > src
            for attr in ("data-src", "data-srcset", "srcset", "src"):
                value = img.get(attr)
                if value and isinstance(value, str):
                    # For srcset attributes, extract the first URL
                    url = (
                        self._extract_first_url_from_srcset(value)
                        if "srcset" in attr
                        else value
                    )
                    if url:
                        return self._resolve_image_url(url)

        return None

    def _extract_first_url_from_srcset(self, srcset: str) -> str | None:
        """Extract the first URL from a srcset attribute value.

        srcset format: "url1 1x, url2 2x" or "url1 100w, url2 200w"

        Args:
            srcset: The srcset attribute value.

        Returns:
            First URL from the srcset or None if empty.
        """
        if not srcset.strip():
            return None
        # Split by comma and get first entry, then extract URL (first part before space)
        first_entry = srcset.split(",")[0].strip()
        if not first_entry:
            return None
        # URL is the first part (before optional descriptor like "1x" or "100w")
        return first_entry.split()[0]

    def _resolve_image_url(self, url: str) -> str:
        """Resolve potentially relative image URL to absolute.

        Args:
            url: Image URL (may be relative or absolute).

        Returns:
            Absolute URL.
        """
        if url.startswith("//"):
            return f"https:{url}"
        elif url.startswith("/"):
            return urljoin(BASE_URL, url)
        return url
