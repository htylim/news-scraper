"""Browser module for headless page rendering."""

from contextlib import suppress

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

# Realistic Chrome User-Agent to avoid bot detection
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class BrowserError(Exception):
    """Exception raised when browser operations fail."""

    def __init__(self, message: str, url: str) -> None:
        """Initialize BrowserError.

        Args:
            message: Error description.
            url: The URL that failed to load.
        """
        self.message = message
        self.url = url
        super().__init__(message)


def fetch_rendered_html(url: str, timeout: int = 30000) -> str:
    """Fetch fully-rendered HTML from a URL using headless browser.

    Launches headless Chrome, navigates to the URL, waits for the page
    to load, and returns the rendered HTML.

    Args:
        url: The URL to fetch.
        timeout: Navigation timeout in milliseconds. Defaults to 30000 (30s).

    Returns:
        The fully-rendered HTML content of the page.

    Raises:
        BrowserError: If browser launch or navigation fails.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel="chrome")
            try:
                context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
                page = context.new_page()
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                # Best-effort extra settling time for dynamic pages.
                with suppress(PlaywrightError):
                    page.wait_for_load_state("networkidle", timeout=5000)
                return page.content()
            finally:
                browser.close()
    except PlaywrightError as e:
        raise BrowserError(str(e), url) from e
