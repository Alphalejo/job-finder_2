"""
GetOnBoard scraper implementation.
Uses Playwright to navigate, handle job search results, and extract details.
Includes comprehensive logging and a standalone execution block for testing.
"""

import logging
import sys
from typing import Any

from playwright.sync_api import sync_playwright
from .base import BaseScraper

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class GetOnBoardScraper(BaseScraper):
    """GetOnBoard job platform scraper inheriting from BaseScraper."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(platform_name="getonboard", config=config)
        self.base_url = self.config.get("base_url", "https://www.getonbrd.com")
        logger.info(f"Initialized GetOnBoardScraper with base URL: {self.base_url}")

    def scrape(self, target_limit: int, existing_links: set[str]) -> list[dict[str, Any]]:
        logger.info(f"Starting scrape run for target: {target_limit} offers...")
        jobs = []

        keyword = self.config.get("keyword", "data analyst")
        
        # Format keyword for the new path-based URL structure (e.g., "data analyst" -> "data-analyst")
        formatted_keyword = keyword.lower().strip().replace(" ", "-")
        search_url = f"{self.base_url}/jobs-{formatted_keyword}"
        logger.info(f"Constructed search URL: {search_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            try:
                page.goto(search_url, timeout=40000)
                page.wait_for_load_state("domcontentloaded")
                self.dismiss_modals(page)
                
                self.scroll_page(page, iterations=2, wait_ms=1500)
                offer_elements = page.query_selector_all("a")
                
                valid_links = []
                for element in offer_elements:
                    href = element.get_attribute("href")
                    # Ensure we grab individual postings and avoid the main search route
                    if href and ("/empleos/" in href or "/jobs/" in href) and not href.startswith(f"/jobs-{formatted_keyword}"):
                        valid_links.append(href)
                
                valid_links = list(set(valid_links))
                logger.info(f"Found {len(valid_links)} unique job links.")
                
                for index, raw_link in enumerate(valid_links):
                    if len(jobs) >= target_limit:
                        break
                        
                    full_link = self.clean_url(raw_link, base_url=self.base_url)
                    if full_link in existing_links:
                        continue
                        
                    detail_page = context.new_page()
                    try:
                        detail_page.goto(full_link, timeout=30000)
                        detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                        self.dismiss_modals(detail_page)
                        
                        role = self.extract_role(
                            detail_page, 
                            primary_selectors=["h1", "h1.job-title", "span.title"]
                        )
                        company = self.extract_company(
                            detail_page, 
                            primary_selectors=["h2", "div.company-name", "strong", "a.company"]
                        )
                        description = self.extract_description(
                            detail_page, 
                            primary_selectors=["div.job-description", "div.job-body", "div#job-body"]
                        )
                        
                        job_data = self.format_job(role=role, company=company, link=full_link, description=description)
                        jobs.append(job_data)
                        existing_links.add(full_link)
                        logger.info(f"✅ Extracted: '{role}' at '{company}'")
                    except Exception as e:
                        logger.error(f"Failed to extract {full_link}. Error: {e}")
                    finally:
                        detail_page.close()

            except Exception as e:
                logger.error(f"Critical error: {e}")
            finally:
                browser.close()

        return jobs

if __name__ == "__main__":
    test_config = {"keyword": "data analyst"}
    scraper = GetOnBoardScraper(config=test_config)
    scraped_jobs = scraper.scrape(target_limit=2, existing_links=set())
    import json
    print(json.dumps(scraped_jobs, indent=2, ensure_ascii=False))