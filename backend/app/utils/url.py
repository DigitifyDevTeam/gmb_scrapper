from urllib.parse import parse_qs, quote, unquote, urlparse, urlunparse

from app.utils.prospect_identity import (
    build_google_maps_profile_url,
    extract_maps_place_id,
    pick_best_maps_source_url,
)

SOCIAL_DOMAINS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
    "linkedin.com",
    "www.linkedin.com",
}


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return ""
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


def extract_domain(url: str) -> str:
    if not url:
        return ""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def is_social_domain(url: str) -> bool:
    domain = extract_domain(url)
    if not domain:
        return False
    return domain in SOCIAL_DOMAINS or any(
        domain.endswith(f".{social}") for social in SOCIAL_DOMAINS
    )


_GOOGLE_OWNED_DOMAINS = frozenset(
    {
        "google.com",
        "google.fr",
        "goo.gl",
        "maps.google.com",
        "g.page",
        "business.google.com",
    }
)


def is_google_owned_url(url: str) -> bool:
    domain = extract_domain(url)
    if not domain:
        return False
    if domain in _GOOGLE_OWNED_DOMAINS:
        return True
    return domain.endswith(".google.com") or domain.endswith(".google.fr")


def unwrap_google_redirect_url(url: str) -> str:
    """Resolve Google /url?q=... tracking links to the destination website."""
    cleaned = url.strip()
    if not cleaned:
        return cleaned

    parsed = urlparse(cleaned)
    host = parsed.netloc.lower()
    if "google." not in host:
        return cleaned

    path = parsed.path.rstrip("/")
    if path not in {"", "/url"}:
        return cleaned

    query = parse_qs(parsed.query)
    for key in ("q", "url"):
        values = query.get(key)
        if values and values[0].strip():
            return unquote(values[0].strip())

    return cleaned


def parse_website_href(href: str | None) -> str | None:
    """Normalize a scraped website href from Google Maps into a clean external URL."""
    if not href or not href.strip():
        return None

    cleaned = unwrap_google_redirect_url(href.strip())
    if cleaned.startswith("//"):
        cleaned = f"https:{cleaned}"
    if not cleaned.startswith(("http://", "https://")):
        return None
    if is_google_owned_url(cleaned):
        return None

    normalized = normalize_url(cleaned)
    return normalized or None


def normalize_maps_url(url: str | None) -> str | None:
    """Normalize a scraped Maps URL while preserving place identity when possible."""
    if not url:
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    source_url = pick_best_maps_source_url(cleaned)
    if not source_url:
        return None

    place_id = extract_maps_place_id(source_url)
    if place_id:
        if place_id.lower().startswith("chij"):
            return (
                "https://www.google.com/maps/search/?api=1"
                f"&query_place_id={quote(place_id)}"
            )
        if place_id.startswith("0x") and ":" in place_id:
            token = quote(place_id, safe="")
            return f"https://www.google.com/maps/place/data=!4m2!3m1!1s{token}"
        if place_id.isdigit():
            return f"https://maps.google.com/maps?cid={place_id}"

    if "!1s" in source_url:
        return source_url.split("?")[0]

    parsed = urlparse(source_url)
    if not parsed.netloc:
        return source_url

    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return normalized or source_url


def resolve_maps_navigation_url(
    *,
    maps_url: str | None,
    maps_place_id: str | None = None,
    business_name: str | None = None,
    address: str | None = None,
    city: str | None = None,
    country: str | None = None,
) -> str | None:
    """Prefer a direct /maps/place/ link so reviews open on the correct business."""
    source = pick_best_maps_source_url(maps_url)
    if source and "/maps/place/" in source:
        return source.split("?")[0]

    place_id = maps_place_id or extract_maps_place_id(source or maps_url or "")
    if place_id:
        return build_google_maps_profile_url(
            business_name=business_name or "",
            address=address,
            city=city,
            country=country,
            maps_place_id=place_id,
            maps_url=source or maps_url,
        )

    normalized = normalize_maps_url(maps_url)
    return normalized or source or maps_url
