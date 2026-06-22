from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeRunResult:
    found: int
    saved: int
    skipped_duplicates: int
    skipped_has_website: int = 0
    saved_leads: int = 0
