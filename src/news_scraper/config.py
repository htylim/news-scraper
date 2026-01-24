"""Central configuration for the news-scraper project."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Database
DATABASE_URL = f"sqlite:///{DATA_DIR}/news_scraper.db"


def ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
