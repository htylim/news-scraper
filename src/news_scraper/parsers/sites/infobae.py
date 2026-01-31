"""Parser for Infobae news site."""

from __future__ import annotations

from typing import cast
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from news_scraper.parsers.base import BaseParser, ParsedArticleData
from news_scraper.parsers.registry import register_parser
from news_scraper.parsers.utils import first_srcset_url, resolve_url


@register_parser("infobae")
class InfobaeParser(BaseParser):
    """Parser for Infobae front page HTML."""

    base_url = "https://www.infobae.com"
    allowed_hosts = {"www.infobae.com", "infobae.com"}

    def iter_article_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Find story card containers."""
        return cast(list[Tag], soup.find_all(class_="story-card-ctn"))

    def parse_article_element(self, element: Tag) -> ParsedArticleData | None:
        """Extract article data from a story-card-ctn element."""
        title = self._extract_headline(element)
        url = self._extract_url(element)
        if not title or not url:
            return None

        return {
            "title": title,
            "url": url,
            "summary": self._extract_summary(element),
            "image_url": self._extract_image_url(element),
        }

    def _extract_headline(self, element: Tag) -> str | None:
        """Extract headline text from article element."""
        h2 = element.find("h2", class_="story-card-hl")
        if h2:
            text: str = h2.get_text(strip=True)
            if text:
                return text

        h2_fallback = element.find("h2")
        if h2_fallback:
            text = h2_fallback.get_text(strip=True)
            if text:
                return text

        return None

    def _extract_url(self, element: Tag) -> str | None:
        """Extract article URL from element."""
        href = element.get("href")
        if href and isinstance(href, str):
            resolved = resolve_url(self.base_url, self.allowed_hosts, href)
            if resolved:
                return resolved

        link = element.find("a", href=True)
        if link:
            href = link.get("href")
            if href and isinstance(href, str):
                return resolve_url(self.base_url, self.allowed_hosts, href)

        return None

    def _extract_summary(self, element: Tag) -> str | None:
        """Extract summary/deck from article element."""
        deck = element.find("h3", class_="story-card-deck")
        if deck:
            text: str = deck.get_text(strip=True)
            if text:
                return text
        return None

    def _extract_image_url(self, element: Tag) -> str | None:
        """Extract image URL from article element."""
        img = element.find("img", class_="story-card-img")
        if not img:
            img = element.find("img")

        if img and isinstance(img, Tag):
            for attr in ("data-src", "data-srcset", "srcset", "src"):
                value = img.get(attr)
                if value and isinstance(value, str):
                    url = first_srcset_url(value) if "srcset" in attr else value
                    if url:
                        return self._resolve_image_url(url)

        return None

    def _resolve_image_url(self, url: str) -> str:
        """Resolve potentially relative image URL to absolute."""
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return urljoin(self.base_url, url)
        return url
