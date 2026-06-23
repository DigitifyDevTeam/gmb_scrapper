from app.utils.url import parse_website_href, unwrap_google_redirect_url


def test_unwrap_google_redirect_url() -> None:
    wrapped = (
        "https://www.google.com/url?q=https://restaurant-dupont.fr/menu"
        "&sa=U&ved=abc"
    )
    assert unwrap_google_redirect_url(wrapped) == "https://restaurant-dupont.fr/menu"


def test_parse_website_href_accepts_direct_url() -> None:
    assert parse_website_href("https://example.com/path") == "https://example.com/path"


def test_parse_website_href_unwraps_google_tracking_link() -> None:
    wrapped = "https://www.google.com/url?q=https://plombier-lyon.fr&sa=U"
    assert parse_website_href(wrapped) == "https://plombier-lyon.fr"


def test_parse_website_href_rejects_google_maps_links() -> None:
    assert parse_website_href("https://www.google.com/maps/place/Test") is None


def test_parse_website_href_adds_scheme_for_protocol_relative_links() -> None:
    assert parse_website_href("//www.cafe-paris.fr") == "https://www.cafe-paris.fr"
