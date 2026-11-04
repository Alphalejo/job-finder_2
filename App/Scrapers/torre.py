"""
Torre scraper implementation.
Uses Playwright to navigate, handle dynamic React/client-side content, and extract job details.
Includes comprehensive logging and a standalone execution block for testing.
"""

import logging
import sys
from typing import Any
import urllib.parse

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

class TorreScraper(BaseScraper):
    """Torre job platform scraper inheriting from BaseScraper."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(platform_name="torre", config=config)
        self.base_url = self.config.get("base_url", "https://torre.ai")
        logger.info(f"Initialized TorreScraper with base URL: {self.base_url}")

    def scrape(self, target_limit: int, existing_links: set[str]) -> list[dict[str, Any]]:
        logger.info(f"Starting scrape run for target: {target_limit} offers...")
        jobs = []

        # Extract search parameters from config
        keyword = self.config.get("keyword", "developer")
        
        # Construct the Torre specific search URL
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"{self.base_url}/jobs?q={encoded_keyword}"
            
        logger.info(f"Constructed search URL: {search_url}")

        with sync_playwright() as p:
            logger.debug("Launching Chromium browser...")
            # Use headless=False if you want to visually debug the browser during standalone testing
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            try:
                logger.info("Navigating to search page...")
                page.goto(search_url, timeout=40000)
                page.wait_for_load_state("networkidle")
                
                logger.info("Attempting to dismiss any initial modals/cookies...")
                self.dismiss_modals(page)
                
                logger.info("Waiting for job offer cards to load...")
                # Torre heavily uses client-side rendering; wait for anchor tags pointing to job posts
                page.wait_for_selector("a[href*='/jobs/']", timeout=20000)
                
                # Scroll to trigger lazy loading of additional job cards
                logger.info("Scrolling page to load additional listings...")
                self.scroll_page(page, iterations=3, wait_ms=2000)
                
                # Retrieve all job card anchor elements
                offer_elements = page.query_selector_all("a[href*='/jobs/']")
                
                # Filter out non-job links (like profile or company links) that might contain '/jobs/'
                valid_links = []
                for element in offer_elements:
                    href = element.get_attribute("href")
                    if href and "/jobs/" in href:
                        valid_links.append(href)
                
                # Deduplicate links found on the page
                valid_links = list(set(valid_links))
                logger.info(f"Found {len(valid_links)} unique job links on the initial page.")
                
                for index, raw_link in enumerate(valid_links):
                    if len(jobs) >= target_limit:
                        logger.info("Target limit reached. Halting extraction loop.")
                        break
                        
                    logger.debug(f"Processing link {index + 1}/{len(valid_links)}")
                    
                    full_link = self.clean_url(raw_link, base_url=self.base_url)
                    
                    if full_link in existing_links:
                        logger.info(f"Duplicate link detected, skipping: {full_link}")
                        continue
                        
                    logger.info(f"New job identified. Navigating to detail page: {full_link}")
                    
                    # Open detail page in a new tab
                    detail_page = context.new_page()
                    try:
                        detail_page.goto(full_link, timeout=30000)
                        # Torre's job descriptions can take a moment to render the text blocks
                        detail_page.wait_for_load_state("networkidle", timeout=15000)
                        self.dismiss_modals(detail_page)
                        
                        # Use BaseScraper's fallback extractors with primary Torre selectors
                        role = self.extract_role(
                            detail_page, 
                            primary_selectors=["h1", "h1.title", "div.job-title"]
                        )
                        company = self.extract_company(
                            detail_page, 
                            primary_selectors=["div.organization", "a.company-name", "h2", "span.org-name"]
                        )
                        description = self.extract_description(
                            detail_page, 
                            primary_selectors=["div.job-description", "div.markdown-body", "article", "div#job-details"]
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
        "keyword": "python developer",
        "base_url": "https://torre.ai"
    }
    
    # Initialize the scraper
    logger.info("--- Starting Standalone Torre Scraper Test ---")
    scraper = TorreScraper(config=test_config)
    
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