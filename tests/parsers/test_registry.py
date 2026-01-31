"""Tests for parser registry."""

import pytest

from news_scraper.parsers import ParserNotFoundError, get_parser
from news_scraper.parsers.sites.infobae import InfobaeParser
from news_scraper.parsers.sites.lanacion import LaNacionParser
from news_scraper.parsers.sites.lapoliticaonline import LaPoliticaOnlineParser


class TestGetParser:
    """Tests for get_parser function."""

    def test_get_infobae_parser(self) -> None:
        """Test getting Infobae parser returns instance."""
        parser = get_parser("infobae")
        assert isinstance(parser, InfobaeParser)

    def test_get_lanacion_parser(self) -> None:
        """Test getting La Nacion parser returns instance."""
        parser = get_parser("lanacion")
        assert isinstance(parser, LaNacionParser)

    def test_get_lapoliticaonline_parser(self) -> None:
        """Test getting La Política Online parser returns instance."""
        parser = get_parser("lapoliticaonline")
        assert isinstance(parser, LaPoliticaOnlineParser)

    def test_get_parser_case_insensitive(self) -> None:
        """Test parser lookup is case insensitive."""
        assert isinstance(get_parser("INFOBAE"), InfobaeParser)
        assert isinstance(get_parser("Infobae"), InfobaeParser)
        assert isinstance(get_parser("LANACION"), LaNacionParser)
        assert isinstance(get_parser("LaNacion"), LaNacionParser)
        assert isinstance(get_parser("LAPOLITICAONLINE"), LaPoliticaOnlineParser)
        assert isinstance(get_parser("LaPoliticaOnline"), LaPoliticaOnlineParser)

    def test_get_parser_unknown_source(self) -> None:
        """Test getting parser for unknown source raises error."""
        with pytest.raises(ParserNotFoundError) as exc_info:
            get_parser("unknown_source")

        assert exc_info.value.source_name == "unknown_source"
        assert "unknown_source" in str(exc_info.value)
