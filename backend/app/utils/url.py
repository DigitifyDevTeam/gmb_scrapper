from urllib.parse import urlparse, urlunparse

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


def normalize_maps_url(url: str | None) -> str | None:
    """Strip Google Maps tracking params and keep a stable place URL."""
    if not url:
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    if not parsed.netloc:
        return cleaned

    # Drop tracking query params; path retains place identity.
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return normalized or cleaned
