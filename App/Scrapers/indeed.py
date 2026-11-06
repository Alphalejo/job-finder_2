"""
Indeed scraper implementation.
Uses Playwright to navigate, handle job search results, and extract details.
Includes comprehensive logging and a standalone execution block for testing.
"""

import logging
import sys
import urllib.parse
from typing import Any

from playwright.sync_api import sync_playwright

from .base import BaseScraper

# Configure detailed logging for this module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class IndeedScraper(BaseScraper):
    """Indeed job platform scraper inheriting from BaseScraper."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(platform_name="indeed", config=config)
        # Defaulting to the Colombian domain to match your location, configurable via dict
        self.base_url = self.config.get("base_url", "https://co.indeed.com")
        logger.info(f"Initialized IndeedScraper with base URL: {self.base_url}")

    def scrape(self, target_limit: int, existing_links: set[str]) -> list[dict[str, Any]]:
        logger.info(f"Starting scrape run for target: {target_limit} offers...")
        jobs = []

        # Extract search parameters from config
        keyword = self.config.get("keyword", "developer")
        location = self.config.get("location", "bogota")
        
        # Construct the Indeed search URL (e.g., /jobs?q=developer&l=bogota)
        encoded_keyword = urllib.parse.quote(keyword)
        encoded_location = urllib.parse.quote(location)
        search_url = f"{self.base_url}/jobs?q={encoded_keyword}&l={encoded_location}"
            
        logger.info(f"Constructed search URL: {search_url}")

        with sync_playwright() as p:
            logger.debug("Launching Chromium browser...")
            # Indeed has strong anti-bot mechanisms. Running with headless=False can sometimes help during testing.
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            try:
                logger.info("Navigating to Indeed search page...")
                page.goto(search_url, timeout=40000)
                
                # Wait for the network to settle
                page.wait_for_load_state("networkidle", timeout=20000)
                
                logger.info("Attempting to dismiss any initial modals/cookies...")
                self.dismiss_modals(page)
                
                logger.info("Waiting for job offer cards to load...")
                
                # Indeed job links typically have the class 'jcs-JobTitle'
                try:
                    page.wait_for_selector("a.jcs-JobTitle", timeout=15000)
                except Exception:
                    logger.warning("Strict selector not found. Indeed might have served a CAPTCHA or modified the DOM. Proceeding to scan all anchors.")

                logger.info("Scrolling page to load additional listings...")
                self.scroll_page(page, iterations=3, wait_ms=2000)
                
                # Retrieve all anchor tags and filter for job links (Indeed job links usually contain '/rc/clk' or 'vjk=')
                logger.info("Scanning DOM for job links...")
                offer_elements = page.query_selector_all("a")
                
                valid_links = []
                for element in offer_elements:
                    href = element.get_attribute("href")
                    if href and ("/rc/clk" in href or "vjk=" in href or "/viewjob" in href):
                        valid_links.append(href)
                
                valid_links = list(set(valid_links))
                logger.info(f"Found {len(valid_links)} unique job links on the initial page.")
                
                if not valid_links:
                    logger.warning("No job links found. Ensure Indeed is not blocking the headless browser.")
                
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
                        detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
                        self.dismiss_modals(detail_page)
                        
                        # Use BaseScraper's fallback extractors with primary Indeed selectors
                        role = self.extract_role(
                            detail_page, 
                            primary_selectors=["h1.jobsearch-JobInfoHeader-title", "h1"]
                        )
                        company = self.extract_company(
                            detail_page, 
                            primary_selectors=["div[data-company-name='true']", "a.css-119xq1n", "span.css-1cxc9zk"]
                        )
                        description = self.extract_description(
                            detail_page, 
                            primary_selectors=["div#jobDescriptionText", "div.jobsearch-jobDescriptionText"]
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
    import os
    
    # Example test configuration
    test_config = {
        "keyword": "python",
        "location": "bogota",
        "base_url": "https://co.indeed.com"
    }
    
    logger.info("--- Starting Standalone Indeed Scraper Test ---")
    scraper = IndeedScraper(config=test_config)
    
    # Run the scrape method with a small target and empty historical link cache
    test_target = 3
    test_existing_links = set()
    
    scraped_jobs = scraper.scrape(
        target_limit=test_target, 
        existing_links=test_existing_links
    )
    
    logger.info("--- Final Output Payload ---")
    import json
    print(json.dumps(scraped_jobs, indent=2, ensure_ascii=False))