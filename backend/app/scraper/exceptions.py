class BulkJobCancelledError(Exception):
    """Raised when a bulk job stop is requested during an in-flight scrape."""

    def __init__(self, bulk_job_id: str) -> None:
        self.bulk_job_id = bulk_job_id
        super().__init__(f"Bulk job {bulk_job_id} was stopped")


class GoogleMapsBlockedError(Exception):
    """Raised when Google shows a CAPTCHA or anti-bot challenge page."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(
            "Google Maps blocked automated access "
            f"({reason}). Pause scraping, solve the challenge manually if using a "
            "visible browser, or wait before resuming."
        )
