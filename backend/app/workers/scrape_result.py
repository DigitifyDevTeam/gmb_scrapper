from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeRunResult:
    found: int
    saved: int
    skipped_duplicates: int
    saved_with_website: int = 0
    saved_leads: int = 0
