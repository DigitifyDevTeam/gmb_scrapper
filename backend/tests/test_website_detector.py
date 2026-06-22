import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.models.enums import WebsiteReason
from app.scraper.website_detector import WebsiteDetector, _strip_html, _to_homepage_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _response(status_code: int, text: str = "") -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text
    return response


def _mock_client(*, get: object) -> AsyncMock:
    client = AsyncMock()
    client.get = AsyncMock(**get)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _run_detect(detector: WebsiteDetector, client: AsyncMock, url: str = "https://example.com/about") -> object:
    with patch("app.scraper.website_detector.httpx.AsyncClient", return_value=client):
        return asyncio.run(detector.detect(url))


# ---------------------------------------------------------------------------
# Unit: _to_homepage_url
# ---------------------------------------------------------------------------

def test_to_homepage_strips_path() -> None:
    assert _to_homepage_url("https://example.com/menu/lunch") == "https://example.com/"
    assert _to_homepage_url("https://example.com") == "https://example.com/"
    assert _to_homepage_url("https://example.com/") == "https://example.com/"
    assert _to_homepage_url("https://example.com/page?id=3") == "https://example.com/"


# ---------------------------------------------------------------------------
# Unit: _strip_html
# ---------------------------------------------------------------------------

def test_strip_html_removes_tags() -> None:
    assert _strip_html("<h1>Hello</h1> <p>World</p>") == "Hello World"
    assert _strip_html("<script>var x=1;</script>OK") == "var x=1; OK"


# ---------------------------------------------------------------------------
# No-URL / Social
# ---------------------------------------------------------------------------

def test_no_url_detection() -> None:
    detector = WebsiteDetector()
    result = asyncio.run(detector.detect(None))
    assert result.has_website is False
    assert result.reason == WebsiteReason.NO_URL


def test_social_only_detection() -> None:
    detector = WebsiteDetector()
    result = asyncio.run(detector.detect("https://www.facebook.com/mybusiness"))
    assert result.has_website is False
    assert result.reason == WebsiteReason.SOCIAL_ONLY


def test_empty_string_detection() -> None:
    detector = WebsiteDetector()
    result = asyncio.run(detector.detect("   "))
    assert result.has_website is False
    assert result.reason == WebsiteReason.NO_URL


# ---------------------------------------------------------------------------
# 4xx / 5xx → under construction
# ---------------------------------------------------------------------------

def test_http_404_is_under_construction() -> None:
    detector = WebsiteDetector()
    client = _mock_client(get={"return_value": _response(404, "Not Found")})

    result = _run_detect(detector, client)

    assert result.has_website is False
    assert result.reason == WebsiteReason.UNDER_CONSTRUCTION


def test_http_500_is_under_construction() -> None:
    detector = WebsiteDetector()
    client = _mock_client(get={"return_value": _response(500, "Internal Server Error")})

    result = _run_detect(detector, client)

    assert result.has_website is False
    assert result.reason == WebsiteReason.UNDER_CONSTRUCTION


def test_http_503_is_under_construction() -> None:
    detector = WebsiteDetector()
    client = _mock_client(get={"return_value": _response(503, "Service Unavailable")})

    result = _run_detect(detector, client)

    assert result.has_website is False
    assert result.reason == WebsiteReason.UNDER_CONSTRUCTION


# ---------------------------------------------------------------------------
# Placeholder homepage → under construction
# ---------------------------------------------------------------------------

def test_tiny_coming_soon_page_is_under_construction() -> None:
    """A short homepage with only 'coming soon' is a placeholder."""
    detector = WebsiteDetector()
    html = "<html><body><h1>Coming Soon</h1><p>We are launching soon!</p></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is False
    assert result.reason == WebsiteReason.UNDER_CONSTRUCTION


def test_tiny_maintenance_page_is_under_construction() -> None:
    detector = WebsiteDetector()
    html = "<html><body><h1>Site en maintenance</h1></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is False
    assert result.reason == WebsiteReason.UNDER_CONSTRUCTION


def test_tiny_en_construction_page_is_under_construction() -> None:
    detector = WebsiteDetector()
    html = "<html><body><p>Site en construction</p></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is False
    assert result.reason == WebsiteReason.UNDER_CONSTRUCTION


# ---------------------------------------------------------------------------
# Real sites with construction-like words → VALID (false-positive prevention)
# ---------------------------------------------------------------------------

def test_full_site_mentioning_maintenance_is_valid() -> None:
    """A rich homepage with >1500 chars that mentions 'maintenance' is a real site."""
    detector = WebsiteDetector()
    long_content = "Bienvenue sur notre site. " * 200  # ~5000 chars
    html = f"<html><body>{long_content}<p>Nous assurons la maintenance de vos locaux.</p></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is True
    assert result.reason == WebsiteReason.VALID


def test_full_site_mentioning_coming_soon_is_valid() -> None:
    """A real site that says 'new feature coming soon' is NOT a placeholder."""
    detector = WebsiteDetector()
    long_content = "Lorem ipsum dolor sit amet. " * 200
    html = f"<html><body>{long_content}<p>Our new catalog is coming soon!</p></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is True
    assert result.reason == WebsiteReason.VALID


def test_full_site_mentioning_en_construction_is_valid() -> None:
    detector = WebsiteDetector()
    long_content = "Description de nos services professionnels. " * 200
    html = f"<html><body>{long_content}<p>Notre nouvelle boutique en construction arrive bientôt !</p></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is True
    assert result.reason == WebsiteReason.VALID


# ---------------------------------------------------------------------------
# Homepage is always checked, not the internal page
# ---------------------------------------------------------------------------

def test_internal_url_checks_homepage_not_internal_page() -> None:
    """Even when GMB gives us /menu, we check /."""
    detector = WebsiteDetector()
    ok = _response(200, "<html><body>" + "x" * 2000 + "</body></html>")
    client = _mock_client(get={"return_value": ok})

    with patch("app.scraper.website_detector.httpx.AsyncClient", return_value=client):
        asyncio.run(detector.detect("https://restaurant.fr/menu/carte"))

    # The GET should have been called with the homepage, not /menu/carte
    actual_url = client.get.call_args[0][0]
    assert actual_url == "https://restaurant.fr/"


# ---------------------------------------------------------------------------
# Network errors → benefit of the doubt → VALID
# ---------------------------------------------------------------------------

def test_timeout_is_valid() -> None:
    detector = WebsiteDetector()
    client = _mock_client(get={"side_effect": httpx.TimeoutException("timeout")})

    result = _run_detect(detector, client)

    assert result.has_website is True
    assert result.reason == WebsiteReason.VALID


def test_connect_error_is_valid() -> None:
    detector = WebsiteDetector()
    client = _mock_client(get={"side_effect": httpx.ConnectError("refused")})

    result = _run_detect(detector, client)

    assert result.has_website is True
    assert result.reason == WebsiteReason.VALID


# ---------------------------------------------------------------------------
# Normal 2xx / 3xx → VALID
# ---------------------------------------------------------------------------

def test_200_normal_page_is_valid() -> None:
    detector = WebsiteDetector()
    html = "<html><body><h1>Welcome</h1><p>Our restaurant serves great food.</p></body></html>"
    client = _mock_client(get={"return_value": _response(200, html)})

    result = _run_detect(detector, client)

    assert result.has_website is True
    assert result.reason == WebsiteReason.VALID
