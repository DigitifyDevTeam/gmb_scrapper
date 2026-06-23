import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import get_settings
from app.models.enums import WebsiteReason
from app.utils.url import extract_domain, is_social_domain, normalize_url

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
}

_MISSING_PAGE_STATUSES = frozenset({404, 410})

# Strong signals when they dominate the page title or headline.
_STRONG_PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"coming\s+soon",
        r"under\s+construction",
        r"site\s+en\s+construction",
        r"en\s+cours\s+de\s+construction",
        r"page\s+en\s+construction",
        r"bient[ôo]t\s+disponible",
        r"domain\s+(for\s+sale|parking|parked)",
        r"site\s+en\s+maintenance",
        r"under\s+maintenance",
    ]
]

# Weak phrases that appear on real business sites (footer, blog posts, etc.).
_WEAK_PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"en\s+maintenance",
    ]
]

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)

# Real SMB sites are often short; only treat very small pages as placeholders.
_MAX_PLACEHOLDER_TEXT_LENGTH = 500
_TINY_PLACEHOLDER_TEXT_LENGTH = 220


@dataclass
class DetectionResult:
    has_website: bool
    reason: WebsiteReason


def _to_homepage_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))


def _candidate_urls(url: str) -> list[str]:
    """Try the GMB URL first, then common alternates bots often need."""
    parsed = urlparse(url)
    candidates: list[str] = []

    def add(candidate: str) -> None:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add(url)

    homepage = _to_homepage_url(url)
    add(homepage)

    host = parsed.netloc.lower()
    if host.startswith("www."):
        add(urlunparse((parsed.scheme, host[4:], parsed.path, parsed.params, parsed.query, parsed.fragment)))
    elif host:
        add(urlunparse((parsed.scheme, f"www.{host}", parsed.path, parsed.params, parsed.query, parsed.fragment)))

    if parsed.scheme == "https":
        add(urlunparse(("http", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)))
    elif parsed.scheme == "http":
        add(urlunparse(("https", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)))

    return candidates


def _strip_html(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _extract_headline(html: str) -> str:
    title_match = _TITLE_RE.search(html)
    h1_match = _H1_RE.search(html)
    parts: list[str] = []
    if title_match:
        parts.append(title_match.group(1))
    if h1_match:
        parts.append(h1_match.group(1))
    return _strip_html(" ".join(parts))


class WebsiteDetector:
    def __init__(self) -> None:
        settings = get_settings()
        self.timeout = settings.website_detection_timeout_seconds
        self.concurrency = settings.website_detection_concurrency
        self._semaphore = asyncio.Semaphore(self.concurrency)

    async def detect(self, website: str | None) -> DetectionResult:
        if not website or not website.strip():
            return DetectionResult(has_website=False, reason=WebsiteReason.NO_URL)

        normalized = normalize_url(website)
        if is_social_domain(normalized):
            return DetectionResult(has_website=False, reason=WebsiteReason.SOCIAL_ONLY)

        if not extract_domain(normalized):
            return DetectionResult(has_website=False, reason=WebsiteReason.NO_URL)

        async with self._semaphore:
            return await self._validate_http(normalized)

    async def detect_batch(self, websites: list[str | None]) -> list[DetectionResult]:
        tasks = [self.detect(website) for website in websites]
        return await asyncio.gather(*tasks)

    async def _validate_http(self, original_url: str) -> DetectionResult:
        """Prefer VALID when uncertain — WAFs and homepage mismatches are common."""
        saw_missing_page = False
        saw_placeholder = False

        for candidate_url in _candidate_urls(original_url):
            response = await self._fetch(candidate_url)
            if response is None:
                return DetectionResult(has_website=True, reason=WebsiteReason.VALID)

            if response.status_code in _MISSING_PAGE_STATUSES:
                saw_missing_page = True
                continue

            if self._is_success_status(response.status_code):
                if self._is_placeholder_homepage(response.text):
                    saw_placeholder = True
                    continue
                return DetectionResult(has_website=True, reason=WebsiteReason.VALID)

            # Bot blocks, auth walls, and transient server errors mean the site exists.
            return DetectionResult(has_website=True, reason=WebsiteReason.VALID)

        if saw_placeholder:
            return DetectionResult(
                has_website=False,
                reason=WebsiteReason.UNDER_CONSTRUCTION,
            )

        if saw_missing_page:
            return DetectionResult(has_website=True, reason=WebsiteReason.VALID)

        return DetectionResult(has_website=True, reason=WebsiteReason.VALID)

    async def _fetch(self, url: str) -> httpx.Response | None:
        last_response: httpx.Response | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=self.timeout,
                    headers=BROWSER_HEADERS,
                ) as client:
                    response = await client.get(url)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
                return None

            last_response = response
            if attempt == 0 and response.status_code in (429, 500, 502, 503, 504):
                continue
            return response

        return last_response

    @staticmethod
    def _is_success_status(status_code: int) -> bool:
        return 200 <= status_code < 300

    @staticmethod
    def _is_placeholder_homepage(html: str) -> bool:
        snippet = html[:50_000]
        visible_text = _strip_html(snippet)
        if len(visible_text) > _MAX_PLACEHOLDER_TEXT_LENGTH:
            return False

        headline = _extract_headline(snippet)
        if headline and any(pattern.search(headline) for pattern in _STRONG_PLACEHOLDER_PATTERNS):
            return True

        if len(visible_text) <= _TINY_PLACEHOLDER_TEXT_LENGTH:
            if any(pattern.search(visible_text) for pattern in _STRONG_PLACEHOLDER_PATTERNS):
                return True
            if any(pattern.search(visible_text) for pattern in _WEAK_PLACEHOLDER_PATTERNS):
                return True

        return False
