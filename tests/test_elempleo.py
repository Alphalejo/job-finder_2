import sys
import os
import pytest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.scrapers.elempleo import ElEmpleoScraper

@patch("app.scrapers.elempleo.sync_playwright")
def test_scrape_success(mock_playwright):
    mock_p, mock_browser, mock_context, mock_page = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_p
    mock_p.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Mock ElEmpleo anchor tags (requires '/ofertas-trabajo/' in href)
    mock_link = MagicMock()
    mock_link.get_attribute.return_value = "/ofertas-trabajo/python-dev/123"
    mock_page.query_selector_all.return_value = [mock_link]
    
    scraper = ElEmpleoScraper(config={"keyword": "python"})
    scraper.extract_role = MagicMock(return_value="Python Dev")
    scraper.extract_company = MagicMock(return_value="Tech Corp")
    scraper.extract_description = MagicMock(return_value="Description")
    
    results = scraper.scrape(target_limit=1, existing_links=set())
    
    assert len(results) == 1
    assert "elempleo.com" in results[0]["link"]