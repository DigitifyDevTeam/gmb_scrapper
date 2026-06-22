from app.scraper.testimonial import parse_rating_from_aria


def test_parse_rating_from_english_aria() -> None:
    assert parse_rating_from_aria("4 stars") == 4.0


def test_parse_rating_from_french_aria() -> None:
    assert parse_rating_from_aria("5 étoiles") == 5.0


def test_parse_rating_from_missing_aria() -> None:
    assert parse_rating_from_aria(None) is None
