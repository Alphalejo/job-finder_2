import sys
import os
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.scrapers.computrabajo import ComputrabajoScraper

def test_scraper_initialization():
    """Test that the scraper reads the config and sets attributes correctly."""
    config = {"keyword": "python", "location": "bogota"}
    scraper = ComputrabajoScraper(config=config)
    
    assert scraper.base_url == "https://co.computrabajo.com"
    assert scraper.config["keyword"] == "python"

@patch("app.scrapers.computrabajo.sync_playwright")
def test_scrape_success(mock_playwright):
    """Test the scraping flow by simulating a browser and fake job cards."""
    
    mock_p = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_p
    
    mock_browser = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser
    
    mock_context = MagicMock()
    mock_browser.new_context.return_value = mock_context
    
    mock_page = MagicMock()
    mock_context.new_page.return_value = mock_page
    
    mock_offer = MagicMock()
    mock_link = MagicMock()
    mock_link.get_attribute.return_value = "/trabajo-de-python"
    mock_offer.query_selector.return_value = mock_link
    mock_page.query_selector_all.return_value = [mock_offer]
    
    scraper = ComputrabajoScraper(config={"keyword": "python"})
    
    scraper.extract_role = MagicMock(return_value="Python Developer")
    scraper.extract_company = MagicMock(return_value="Tech Corp")
    scraper.extract_description = MagicMock(return_value="Great job description.")
    
    results = scraper.scrape(target_limit=1, existing_links=set())
    
    assert len(results) == 1
    assert results[0]["role"] == "Python Developer"
    assert results[0]["company"] == "Tech Corp"
    assert "https://co.computrabajo.com/trabajo-de-python" in results[0]["link"]