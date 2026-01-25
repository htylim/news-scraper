"""Tests for parser registry."""

import pytest

from news_scraper.parsers import ParserNotFoundError, get_parser
from news_scraper.parsers.infobae import InfobaeParser


class TestGetParser:
    """Tests for get_parser function."""

    def test_get_infobae_parser(self) -> None:
        """Test getting Infobae parser returns instance."""
        parser = get_parser("infobae")
        assert isinstance(parser, InfobaeParser)

    def test_get_parser_case_insensitive(self) -> None:
        """Test parser lookup is case insensitive."""
        assert isinstance(get_parser("INFOBAE"), InfobaeParser)
        assert isinstance(get_parser("Infobae"), InfobaeParser)

    def test_get_parser_unknown_source(self) -> None:
        """Test getting parser for unknown source raises error."""
        with pytest.raises(ParserNotFoundError) as exc_info:
            get_parser("unknown_source")

        assert exc_info.value.source_name == "unknown_source"
        assert "unknown_source" in str(exc_info.value)
