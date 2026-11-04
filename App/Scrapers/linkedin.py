"""
LinkedIn scraper wrapper maintaining complete compatibility with existing linkedin_scraper.py.
"""

from typing import Any

from .base import BaseScraper


class LinkedInScraper(BaseScraper):
    """Wraps proven LinkedIn scraper logic preserving all existing considerations."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(platform_name="linkedin", config=config)

    def scrape(self, target_limit: int, existing_links: set[str]) -> list[dict[str, Any]]:
        print(f"\n[LinkedInScraper] Starting scrape run for target: {target_limit} offers...")
        try:
            import linkedin_scraper

            jobs = linkedin_scraper.run_scraper(
                target_limit=target_limit,
                save_to_storage=False,
                existing_links=existing_links,
            )
            # Ensure platform key is tagged
            for job in jobs:
                job.setdefault("platform", "linkedin")
            print(f"[LinkedInScraper] Collected {len(jobs)} offers.")
            return jobs
        except Exception as e:
            print(f"[LinkedInScraper] Encountered error during scraping: {e}")
            return []
