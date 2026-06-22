from app.models.enums import WebsiteReason
from app.scraper.website_detector import DetectionResult, WebsiteDetector
from app.services.normalization_service import NormalizedBusiness


class WebsiteDetectionService:
    def __init__(self) -> None:
        self.detector = WebsiteDetector()

    async def enrich_batch(
        self,
        businesses: list[NormalizedBusiness],
    ) -> list[tuple[NormalizedBusiness, DetectionResult]]:
        websites = [business.website for business in businesses]
        results = await self.detector.detect_batch(websites)
        return list(zip(businesses, results, strict=True))

    async def detect_single(self, website: str | None) -> DetectionResult:
        return await self.detector.detect(website)

    @staticmethod
    def reason_label(reason: WebsiteReason) -> str:
        labels = {
            WebsiteReason.NO_URL: "Pas de site web",
            WebsiteReason.DNS_FAILURE: "Échec DNS",
            WebsiteReason.HTTP_FAILURE: "En construction",
            WebsiteReason.SOCIAL_ONLY: "Réseaux sociaux uniquement",
            WebsiteReason.UNDER_CONSTRUCTION: "En construction",
            WebsiteReason.VALID: "Site valide",
        }
        return labels[reason]
