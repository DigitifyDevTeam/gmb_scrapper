from decimal import Decimal

from app.scraper.business_parser import BusinessParser


def test_parse_rating_prefers_decimal_value() -> None:
    parser = BusinessParser()
    assert parser._parse_rating("4,8 étoiles") == Decimal("4.8")
    assert parser._parse_rating("Note : 4 sur 5") == Decimal("4")


def test_parse_review_count_handles_french_spacing() -> None:
    parser = BusinessParser()
    assert parser._parse_review_count("1\u202f234 avis") == 1234
    assert parser._parse_review_count("(42)") == 42
