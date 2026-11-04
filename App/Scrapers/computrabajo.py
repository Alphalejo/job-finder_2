"""
Computrabajo scraper implementation.
Uses Playwright to navigate, handle dynamic content, and extract job details.
Includes comprehensive logging and a standalone execution block for testing.
"""

import logging
import sys
from typing import Any

# Import Playwright for browser automation
from playwright.sync_api import sync_playwright

from .base import BaseScraper

# Configure detailed logging for this module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class ComputrabajoScraper(BaseScraper):
    """Computrabajo job platform scraper inheriting from BaseScraper."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(platform_name="computrabajo", config=config)
        # Defaulting to Colombia; this can be parameterized in the config
        self.base_url = self.config.get("base_url", "https://co.computrabajo.com")
        logger.info(f"Initialized ComputrabajoScraper with base URL: {self.base_url}")

    def scrape(self, target_limit: int, existing_links: set[str]) -> list[dict[str, Any]]:
        logger.info(f"Starting scrape run for target: {target_limit} offers...")
        jobs = []

        # Extract search parameters from config or use defaults
        keyword = self.config.get("keyword", "desarrollador")
        location = self.config.get("location", "")
        
        # Construct the Computrabajo specific search URL
        search_url = f"{self.base_url}/trabajo-de-{keyword}"
        if location:
            search_url += f"-en-{location}"
            
        logger.info(f"Constructed search URL: {search_url}")

        with sync_playwright() as p:
            logger.debug("Launching Chromium browser...")
            # Use headless=False if you want to visually debug the browser during standalone testing
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            try:
                logger.info("Navigating to search page...")
                page.goto(search_url, timeout=30000)
                
                logger.info("Attempting to dismiss any initial modals/cookies...")
                self.dismiss_modals(page)
                
                logger.info("Waiting for job offer cards to load (article.box_offer)...")
                # Wait until at least one job card is present on the DOM
                page.wait_for_selector("article.box_offer", timeout=15000)
                
                # Scroll to trigger lazy loading of additional job cards
                logger.info("Scrolling page to load additional listings...")
                self.scroll_page(page, iterations=2, wait_ms=1500)
                
                # Retrieve all job card elements
                offer_elements = page.query_selector_all("article.box_offer")
                logger.info(f"Found {len(offer_elements)} job cards on the initial page.")
                
                for index, offer in enumerate(offer_elements):
                    if len(jobs) >= target_limit:
                        logger.info("Target limit reached. Halting extraction loop.")
                        break
                        
                    logger.debug(f"Processing card {index + 1}/{len(offer_elements)}")
                    
                    # Extract the job listing URL
                    link_element = offer.query_selector("a.js-o-link")
                    if not link_element:
                        logger.warning("No link element found in this card. Skipping.")
                        continue
                        
                    raw_link = link_element.get_attribute("href")
                    full_link = self.clean_url(raw_link, base_url=self.base_url)
                    
                    if full_link in existing_links:
                        logger.info(f"Duplicate link detected, skipping: {full_link}")
                        continue
                        
                    logger.info(f"New job identified. Navigating to detail page: {full_link}")
                    
                    # Open detail page in a new tab to ensure full description extraction
                    detail_page = context.new_page()
                    try:
                        detail_page.goto(full_link, timeout=20000)
                        self.dismiss_modals(detail_page)
                        
                        # Use BaseScraper's fallback extractors with primary Computrabajo selectors
                        role = self.extract_role(
                            detail_page, 
                            primary_selectors=["h1.title", "h1.fwB"]
                        )
                        company = self.extract_company(
                            detail_page, 
                            primary_selectors=["a.fs16", "p.fs16", "div.fs16"]
                        )
                        description = self.extract_description(
                            detail_page, 
                            primary_selectors=["div.box_detail", "div.fs16", "p.mbB"]
                        )
                        
                        # Format job to guarantee schema compliance
                        job_data = self.format_job(
                            role=role,
                            company=company,
                            link=full_link,
                            description=description
                        )
                        
                        jobs.append(job_data)
                        existing_links.add(full_link)
                        
                        logger.info(f"✅ Successfully extracted: '{role}' at '{company}'")
                        
                    except Exception as e:
                        logger.error(f"Failed to extract details from {full_link}. Error: {e}")
                    finally:
                        logger.debug("Closing detail page tab.")
                        detail_page.close()

            except Exception as e:
                logger.error(f"Critical error during main page scraping execution: {e}")
            finally:
                logger.info("Cleaning up and closing browser context.")
                browser.close()

        logger.info(f"Scrape completed successfully. Collected {len(jobs)} total offers.")
        return jobs


# ==============================================================================
# STANDALONE EXECUTION BLOCK FOR INDIVIDUAL TESTING
# ==============================================================================
if __name__ == "__main__":
    # Example test configuration
    test_config = {
        "keyword": "python",
        "location": "bogota",
        "base_url": "https://co.computrabajo.com"
    }
    
    # Initialize the scraper
    logger.info("--- Starting Standalone Computrabajo Scraper Test ---")
    scraper = ComputrabajoScraper(config=test_config)
    
    # Run the scrape method with a small target and empty historical link cache
    test_target = 3
    test_existing_links = set()
    
    scraped_jobs = scraper.scrape(
        target_limit=test_target, 
        existing_links=test_existing_links
    )
    
    # Output the final pipeline-ready JSON structure
    logger.info("--- Final Output Payload ---")
    import json
    print(json.dumps(scraped_jobs, indent=2, ensure_ascii=False))