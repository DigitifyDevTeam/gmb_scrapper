from app.scraper.testimonial import (
    build_testimonial_place_key,
    business_names_match,
    parse_rating_from_aria,
)
from app.utils.url import resolve_maps_navigation_url


def test_parse_rating_from_english_aria() -> None:
    assert parse_rating_from_aria("4 stars") == 4.0


def test_parse_rating_from_french_aria() -> None:
    assert parse_rating_from_aria("5 étoiles") == 5.0
    assert parse_rating_from_aria("4,5 étoiles") == 4.5


def test_parse_rating_from_missing_aria() -> None:
    assert parse_rating_from_aria(None) is None


def test_business_names_match_ignores_accents_and_suffix() -> None:
    assert business_names_match("Café du Marché", "Cafe du Marche")
    assert business_names_match("Restaurant Le Petit Bistrot", "Le Petit Bistrot")


def test_build_testimonial_place_key_prefers_place_id() -> None:
    assert (
        build_testimonial_place_key(
            maps_place_id="ChIJabc123",
            maps_url="https://www.google.com/maps/place/foo",
        )
        == "place:chijabc123"
    )


def test_resolve_maps_navigation_url_prefers_place_path() -> None:
    url = resolve_maps_navigation_url(
        maps_url="https://www.google.com/maps/place/Cafe+Paris/data=!4m2!3m1!1s0x123",
    )
    assert url == "https://www.google.com/maps/place/Cafe+Paris/data=!4m2!3m1!1s0x123"
