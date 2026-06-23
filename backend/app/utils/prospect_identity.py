import re
from urllib.parse import quote, quote_plus, unquote, urlparse

from app.utils.address import normalize_address
from app.utils.phone import normalize_phone

_PLACE_ID_PATTERNS = (
    re.compile(r"!1s([^!&?]+)"),
    re.compile(r"!16s([^!&?]+)"),
    re.compile(r"(ChIJ[\w-]+)"),
    re.compile(r"[?&]place_id=([^&]+)"),
    re.compile(r"[?&]q=place_id:([^&]+)"),
    re.compile(r"[?&]cid=(\d+)"),
)

_CHIJ_PLACE_ID_RE = re.compile(r"^chij[\w-]+$", re.IGNORECASE)
_MAPS_COORD_SUFFIX = re.compile(r"/@[^/]+$")
_GOOGLE_MAPS_HOSTS = ("google.com", "maps.google.com")


def normalize_business_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip().lower())
    return cleaned


def extract_maps_place_id(url: str | None) -> str | None:
    if not url:
        return None

    for pattern in _PLACE_ID_PATTERNS:
        match = pattern.search(url)
        if not match:
            continue
        candidate = unquote(match.group(1)).strip()
        if candidate:
            return candidate

    return None


def _absolute_maps_url(url: str) -> str:
    cleaned = url.strip()
    if cleaned.startswith("//"):
        return f"https:{cleaned}"
    if cleaned.startswith("/"):
        return f"https://www.google.com{cleaned}"
    return cleaned


def pick_best_maps_source_url(*urls: str | None) -> str | None:
    """Prefer the listing link tied to the card over a possibly stale page URL."""
    candidates: list[str] = []
    for raw in urls:
        if not raw:
            continue
        absolute = _absolute_maps_url(raw)
        if "/maps/place" in absolute or "maps.google.com" in absolute:
            candidates.append(absolute)

    if not candidates:
        return None

    for candidate in candidates:
        if extract_maps_place_id(candidate):
            return candidate

    return max(candidates, key=len)


def build_google_maps_profile_url(
    *,
    business_name: str,
    address: str | None = None,
    city: str | None = None,
    country: str | None = None,
    maps_place_id: str | None = None,
    maps_url: str | None = None,
) -> str | None:
    """Build a stable Google Maps link that opens the correct business profile."""
    place_id = (maps_place_id or extract_maps_place_id(maps_url) or "").strip()
    if place_id:
        if _CHIJ_PLACE_ID_RE.match(place_id):
            return (
                "https://www.google.com/maps/search/?api=1"
                f"&query={quote_plus(business_name.strip())}"
                f"&query_place_id={quote(place_id)}"
            )
        if place_id.startswith("0x") and ":" in place_id:
            token = quote(place_id, safe="")
            return f"https://www.google.com/maps/place/data=!4m2!3m1!1s{token}"
        if place_id.isdigit():
            return f"https://maps.google.com/maps?cid={place_id}"

    source_url = pick_best_maps_source_url(maps_url)
    if source_url and "!1s" in source_url:
        return source_url.split("?")[0]

    query_parts = [business_name.strip()]
    if address and address.strip():
        query_parts.append(address.strip())
    if city and city.strip():
        address_lower = (address or "").lower()
        if city.strip().lower() not in address_lower:
            query_parts.append(city.strip())
    if country and country.strip():
        query_parts.append(country.strip())

    query = ", ".join(part for part in query_parts if part)
    if query:
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"

    if source_url:
        parsed = urlparse(source_url)
        if parsed.netloc and any(host in parsed.netloc for host in _GOOGLE_MAPS_HOSTS):
            return source_url.split("?")[0]

    return None


def canonical_maps_path(url: str) -> str | None:
    parsed = urlparse(url)
    if "/maps/place/" not in parsed.path.lower():
        return None

    path = unquote(parsed.path).lower().replace("+", " ")
    path = _MAPS_COORD_SUFFIX.sub("", path)
    path = re.sub(r"\s+", " ", path).strip()
    return path or None


def build_prospect_dedupe_key(
    *,
    business_name: str,
    address: str | None = None,
    phone: str | None = None,
    maps_url: str | None = None,
    country: str | None = None,
) -> tuple[str, str | None]:
    """Return a stable (dedupe_key, maps_place_id) pair for global prospect identity."""
    place_id = extract_maps_place_id(maps_url)
    if place_id:
        return f"place:{place_id.lower()}", place_id.lower()

    source_url = pick_best_maps_source_url(maps_url)
    if source_url:
        path = canonical_maps_path(source_url)
        if path:
            return f"maps:{path}", None

    if phone:
        normalized_phone = normalize_phone(phone, country or "")
        digits = re.sub(r"\D", "", normalized_phone or "")
        if len(digits) >= 9:
            return f"phone:{digits}", None

    norm_name = normalize_business_name(business_name)
    norm_addr = (normalize_address(address) or "").lower()
    return f"name:{norm_name}|addr:{norm_addr}", place_id
