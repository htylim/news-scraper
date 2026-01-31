"""Parser for La Nacion news site."""

from typing import TypedDict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from news_scraper.logging import get_logger
from news_scraper.parsers.base import ParsedArticle, Parser


class _ParsedData(TypedDict):
    """Internal type for parsed article data before creating ParsedArticle."""

    headline: str
    url: str
    summary: str | None
    image_url: str | None


# Base URL for resolving relative links
BASE_URL = "https://www.lanacion.com.ar"


class LaNacionParser(Parser):
    """Parser for La Nacion front page HTML.

    Extracts articles from La Nacion's HTML structure. Articles are identified
    by `<article>` elements with class "ln-card".
    """

    def parse(self, html: str) -> list[ParsedArticle]:
        """Parse La Nacion HTML and extract articles.

        Extracts ALL articles found on the page, deduplicates by URL
        (keeping first occurrence), assigns positions, and logs errors
        for individual articles that fail to parse.

        Args:
            html: Raw HTML content from La Nacion's front page.

        Returns:
            List of unique ParsedArticle objects with positions.
            Empty list if no articles found.
        """
        log = get_logger()
        soup = BeautifulSoup(html, "lxml")
        articles: list[ParsedArticle] = []
        seen_urls: set[str] = set()
        position = 0  # Will be incremented before use (1-based)

        # Find all article cards with ln-card class
        article_elements = soup.find_all("article", class_="ln-card")

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
                # Log warning with stack trace and continue with next article
                log.warning("Failed to parse article element", exc_info=True)
                continue

        return articles

    def _parse_article_element(self, element: Tag) -> _ParsedData | None:
        """Extract article data from an ln-card article element.

        Args:
            element: BeautifulSoup Tag containing article data.

        Returns:
            Dict with article fields if extraction successful, None otherwise.
        """
        url = self._extract_url(element)
        headline = self._extract_headline(element)

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

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element.

        Looks for anchor with ln-link class and validates the URL is from
        La Nacion's domain.

        Args:
            element: Article container Tag.

        Returns:
            Absolute URL or None if not found or rejected.
        """
        log = get_logger()

        # Find anchor with ln-link class
        link = element.find("a", class_="ln-link")
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = self._resolve_article_url(href)
                if resolved:
                    return resolved
                log.debug("Rejected URL from ln-link", href=href)

        # Fallback: any anchor with href
        link = element.find("a", href=True)
        if link and isinstance(link, Tag):
            href = link.get("href")
            if href and isinstance(href, str):
                resolved = self._resolve_article_url(href)
                if resolved:
                    return resolved
                log.debug("Rejected URL from fallback link", href=href)

        return None

    def _resolve_article_url(self, href: str) -> str | None:
        """Resolve href to absolute URL if it's from La Nacion's domain.

        Args:
            href: URL string (relative or absolute).

        Returns:
            Absolute URL if valid, None if external/rejected/invalid.
        """
        # Reject empty or fragment-only hrefs
        stripped = href.strip()
        if not stripped or stripped.startswith("#"):
            return None

        # Allowlist of valid La Nacion hostnames
        allowed_hosts = {"www.lanacion.com.ar", "lanacion.com.ar"}

        # Use urljoin to resolve relative and protocol-relative URLs
        resolved = urljoin(BASE_URL, href)
        parsed = urlparse(resolved)

        # Check if the resolved URL is from an allowed host
        if parsed.netloc not in allowed_hosts:
            return None

        # Reject root path or empty path (homepage, not an article)
        if not parsed.path or parsed.path == "/":
            return None

        return self._normalize_url(resolved)

    def _normalize_url(self, url: str) -> str:
        """Normalize article URL before deduplication.

        Strips fragments and all query params. La Nacion article URLs
        don't require query params; they're typically tracking params.
        """
        parsed = urlparse(url)
        return parsed._replace(query="", fragment="").geturl()

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from article element.

        La Nacion uses h1 for featured articles and h2 for regular articles.
        When both h1 and h2 exist, h1 is the headline.

        Args:
            element: Article container Tag.

        Returns:
            Headline text or None if not found.
        """
        # Try h1 first (featured articles)
        h1 = element.find("h1")
        if h1:
            # strip=False keeps space between siblings; then strip full result
            text = (h1.get_text(strip=False) or "").strip()
            if text:
                return text

        # Fall back to h2 (regular articles)
        h2 = element.find("h2")
        if h2:
            text = (h2.get_text(strip=False) or "").strip()
            if text:
                return text

        return None

    def _extract_summary(self, element: Tag) -> str | None:
        """Extract summary from article element.

        Summary is in h3 when present. If article has h1+h2, the h2 is the summary.

        Args:
            element: Article container Tag.

        Returns:
            Summary text or None if not found.
        """
        # Check if article has both h1 (headline) and h2 (summary)
        h1 = element.find("h1")
        h2 = element.find("h2")

        if h1 and h2:
            # When h1 exists, h2 is the summary
            text: str = h2.get_text(strip=True)
            if text:
                return text

        # Otherwise, check for h3 as summary
        h3 = element.find("h3")
        if h3:
            text = h3.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element.

        La Nacion uses picture elements with img inside.
        Images are typically served from CDN with absolute URLs.

        Args:
            element: Article container Tag.

        Returns:
            Absolute image URL or None if not found.
        """
        # Find img inside the article
        img = element.find("img")

        if img and isinstance(img, Tag):
            # Try src first (most common), then data-src for lazy loading
            for attr in ("src", "data-src"):
                src = img.get(attr)
                if src and isinstance(src, str):
                    return self._resolve_image_url(src)

            # Fall back to srcset/data-srcset for responsive images
            for attr in ("srcset", "data-srcset"):
                srcset = img.get(attr)
                if srcset and isinstance(srcset, str):
                    candidate = self._first_srcset_url(srcset)
                    if candidate:
                        return self._resolve_image_url(candidate)

        return None

    def _first_srcset_url(self, srcset: str) -> str | None:
        """Extract first URL from a srcset string."""
        first = srcset.split(",")[0].strip()
        if not first:
            return None
        return first.split()[0]

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
