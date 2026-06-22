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

# Patterns that indicate a placeholder/parked homepage — NOT a real site.
# Matched against visible text stripped of HTML tags, so a normal page
# that casually mentions "maintenance" won't be caught.
_PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"coming\s+soon",
        r"under\s+construction",
        r"site\s+en\s+construction",
        r"en\s+cours\s+de\s+construction",
        r"page\s+en\s+construction",
        r"en\s+maintenance",
        r"site\s+en\s+maintenance",
        r"under\s+maintenance",
        r"bient[ôo]t\s+disponible",
    ]
]

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

# A real site's homepage typically has > 500 chars of visible text.
# Placeholder pages are tiny: a logo, one sentence, and that's it.
_MAX_PLACEHOLDER_TEXT_LENGTH = 1500


@dataclass
class DetectionResult:
    has_website: bool
    reason: WebsiteReason


def _to_homepage_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))


def _strip_html(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


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

        homepage = _to_homepage_url(normalized)

        async with self._semaphore:
            return await self._validate_http(homepage)

    async def detect_batch(self, websites: list[str | None]) -> list[DetectionResult]:
        tasks = [self.detect(website) for website in websites]
        return await asyncio.gather(*tasks)

    async def _validate_http(self, homepage_url: str) -> DetectionResult:
        """Only "en construction" rules decide has_website=false. Everything else is live."""
        headers = {"User-Agent": BROWSER_USER_AGENT}
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                headers=headers,
            ) as client:
                response = await client.get(homepage_url)

            if self._is_error_status(response.status_code):
                return DetectionResult(
                    has_website=False,
                    reason=WebsiteReason.UNDER_CONSTRUCTION,
                )

            if self._is_placeholder_homepage(response.text):
                return DetectionResult(
                    has_website=False,
                    reason=WebsiteReason.UNDER_CONSTRUCTION,
                )

            return DetectionResult(has_website=True, reason=WebsiteReason.VALID)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
            return DetectionResult(has_website=True, reason=WebsiteReason.VALID)

    @staticmethod
    def _is_error_status(status_code: int) -> bool:
        return 400 <= status_code <= 599

    @staticmethod
    def _is_placeholder_homepage(html: str) -> bool:
        visible_text = _strip_html(html[:50_000])
        if len(visible_text) > _MAX_PLACEHOLDER_TEXT_LENGTH:
            return False
        return any(p.search(visible_text) for p in _PLACEHOLDER_PATTERNS)
