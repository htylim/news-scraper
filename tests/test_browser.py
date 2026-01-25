"""Tests for the browser module."""

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.browser import BrowserError, fetch_rendered_html


class TestFetchRenderedHtml:
    """Tests for fetch_rendered_html function."""

    def test_returns_page_content(self) -> None:
        """Test that page HTML content is returned."""
        mock_html = "<html><body>Test content</body></html>"

        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = mock_html

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            result = fetch_rendered_html("https://example.com")

            assert result == mock_html
            mock_page.goto.assert_called_once_with(
                "https://example.com", timeout=30000, wait_until="domcontentloaded"
            )
            mock_page.wait_for_load_state.assert_called_once_with(
                "networkidle", timeout=5000
            )

    def test_browser_closed_on_success(self) -> None:
        """Test browser is closed after successful fetch."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com")

            mock_browser.close.assert_called_once()

    def test_browser_closed_on_navigation_error(self) -> None:
        """Test browser is closed even when navigation fails."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            # Import PlaywrightError to raise it
            from playwright.sync_api import Error as PlaywrightError

            mock_page.goto.side_effect = PlaywrightError("Navigation failed")

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            with pytest.raises(BrowserError, match="Navigation failed"):
                fetch_rendered_html("https://example.com")

            mock_browser.close.assert_called_once()

    def test_custom_timeout(self) -> None:
        """Test custom timeout is passed to page.goto."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com", timeout=60000)

            mock_page.goto.assert_called_once_with(
                "https://example.com", timeout=60000, wait_until="domcontentloaded"
            )
            mock_page.wait_for_load_state.assert_called_once_with(
                "networkidle", timeout=5000
            )

    def test_launches_chrome_headless(self) -> None:
        """Test browser launches Chrome in headless mode."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_chromium = mock_pw.return_value.__enter__.return_value.chromium
            mock_chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com")

            mock_chromium.launch.assert_called_once_with(
                headless=True, channel="chrome"
            )

    def test_sets_custom_user_agent(self) -> None:
        """Test browser context is created with custom user agent."""
        with patch("news_scraper.browser.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_page.content.return_value = "<html></html>"

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = (
                mock_browser
            )
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            fetch_rendered_html("https://example.com")

            # Verify new_context was called with a user_agent parameter
            mock_browser.new_context.assert_called_once()
            call_kwargs = mock_browser.new_context.call_args.kwargs
            assert "user_agent" in call_kwargs
            assert "Mozilla/5.0" in call_kwargs["user_agent"]
