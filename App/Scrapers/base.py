"""
Base scraper class providing resilient HTML extraction, modal dismissal,
URL sanitization, and fallback heuristics for front-end structure changes.
"""

import re
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

# Standard realistic browser headers to prevent bot-detection on public pages
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Resilient general selectors to survive Frontend changes
GENERAL_ROLE_SELECTORS = [
    "h1",
    "h2",
    "h3",
    "[data-test*='title' i]",
    "[data-testid*='title' i]",
    "[data-qa*='title' i]",
    "[class*='job-title' i]",
    "[class*='jobTitle' i]",
    "[class*='title' i]",
    "[class*='position' i]",
    "[class*='role' i]",
    "a.js-o-link",
]

GENERAL_COMPANY_SELECTORS = [
    "[data-test*='company' i]",
    "[data-testid*='company' i]",
    "[data-qa*='company' i]",
    "[data-test*='employer' i]",
    "[class*='company' i]",
    "[class*='employer' i]",
    "[class*='enterprise' i]",
    "[class*='organization' i]",
    "[class*='subtitle' i]",
    "[class*='org' i]",
    "[class*='fc_base' i]",
    "[class*='info-company' i]",
]

GENERAL_DESCRIPTION_SELECTORS = [
    "[data-test*='description' i]",
    "[data-testid*='description' i]",
    "[data-qa*='description' i]",
    "[class*='job-description' i]",
    "[class*='description' i]",
    "[class*='jobDescription' i]",
    "[class*='detail' i]",
    "[class*='details' i]",
    "[class*='summary' i]",
    "[class*='job-body' i]",
    "article",
    "main",
    "section",
]

MODAL_DISMISS_SELECTORS = [
    "button.modal__dismiss",
    ".modal__overlay .modal__dismiss",
    "button[aria-label*='close' i]",
    "button[aria-label*='cerrar' i]",
    "[data-dismiss='modal']",
    "button:has-text('Aceptar')",
    "button:has-text('Accept')",
    "button:has-text('Continuar sin')",
    "button:has-text('Close')",
    "button:has-text('Cerrar')",
    "[id*='cookie'] button",
    "[class*='cookie'] button",
]


class BaseScraper(ABC):
    """Abstract base scraper with resilient fallback logic for all job platforms."""

    def __init__(self, platform_name: str, config: dict[str, Any] | None = None):
        self.platform_name = platform_name
        self.config = config or {}
        self.user_agent = USER_AGENT

    @abstractmethod
    def scrape(self, target_limit: int, existing_links: set[str]) -> list[dict[str, Any]]:
        """
        Execute public job search for this platform without logging in.

        Args:
            target_limit: Target number of new job offers to fetch.
            existing_links: Set of historical job URLs to filter out duplicates.

        Returns:
            List of job offer dicts with standardized keys:
            ['role', 'company', 'link', 'jobDescription', 'scrapedAt', 'platform']
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Resilient Extraction Heuristics
    # ------------------------------------------------------------------

    def clean_text(self, text: Any) -> str:
        """Strip HTML tags, collapse redundant whitespaces, and trim."""
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        # Remove HTML tags if present
        clean = re.sub(r"<[^>]+>", " ", text)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def clean_url(self, url: str | None, base_url: str = "") -> str:
        """Resolves relative URLs and strips analytics tracking parameters."""
        if not url:
            return ""
        full_url = urllib.parse.urljoin(base_url, url)
        # Separate base path and query parameters
        parsed = urllib.parse.urlparse(full_url)
        # Tracking params to discard
        tracking_prefixes = ("utm_", "trk", "tracking", "fbclid", "gclid", "ref", "source")
        if parsed.query:
            query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            cleaned_pairs = [
                (k, v)
                for k, v in query_pairs
                if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)
            ]
            new_query = urllib.parse.urlencode(cleaned_pairs)
            parsed = parsed._replace(query=new_query)
        # If there's no query, strip trailing hash/fragments
        return urllib.parse.urlunparse(parsed).rstrip("#")

    def extract_field_with_fallbacks(
        self,
        element: Any,
        primary_selectors: list[str] | None = None,
        general_selectors: list[str] | None = None,
        default: str = "",
    ) -> str:
        """
        Tries primary platform-specific selectors first, falling back to general
        semantic selectors if the platform updated its front-end markup.
        """
        if not element:
            return default

        selectors = (primary_selectors or []) + (general_selectors or [])
        for selector in selectors:
            try:
                target = element.query_selector(selector)
                if target:
                    text = target.inner_text().strip()
                    if text:
                        return self.clean_text(text)
            except Exception:
                continue

        return default

    def extract_role(self, element: Any, primary_selectors: list[str] | None = None) -> str:
        """Extract job role title using platform selectors with general fallback."""
        return self.extract_field_with_fallbacks(
            element,
            primary_selectors=primary_selectors,
            general_selectors=GENERAL_ROLE_SELECTORS,
            default="Unknown Role",
        )

    def extract_company(self, element: Any, primary_selectors: list[str] | None = None) -> str:
        """Extract company name using platform selectors with general fallback."""
        return self.extract_field_with_fallbacks(
            element,
            primary_selectors=primary_selectors,
            general_selectors=GENERAL_COMPANY_SELECTORS,
            default="Unknown Company",
        )

    def extract_description(self, element: Any, primary_selectors: list[str] | None = None) -> str:
        """Extract job description text using platform selectors with general fallback."""
        return self.extract_field_with_fallbacks(
            element,
            primary_selectors=primary_selectors,
            general_selectors=GENERAL_DESCRIPTION_SELECTORS,
            default="No Description Available",
        )

    # ------------------------------------------------------------------
    # Browser Interaction Guards
    # ------------------------------------------------------------------

    def dismiss_modals(self, page: Any) -> None:
        """Dismiss common modals, overlays, cookie consents, or sign-in prompts."""
        for selector in MODAL_DISMISS_SELECTORS:
            try:
                dismiss_btn = page.query_selector(selector)
                if dismiss_btn and dismiss_btn.is_visible():
                    dismiss_btn.click(timeout=1000)
                    page.wait_for_timeout(300)
            except Exception:
                continue

    def scroll_page(self, page: Any, iterations: int = 3, wait_ms: int = 1500) -> None:
        """Scrolls the page down incrementally to trigger lazy-loaded listings."""
        try:
            for _ in range(iterations):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                page.wait_for_timeout(wait_ms)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Output Schema Formatter
    # ------------------------------------------------------------------

    def format_job(self, role: str, company: str, link: str, description: str) -> dict[str, Any]:
        """Ensures the job offer conforms strictly to the downstream pipeline format."""
        return {
            "role": role or "Unknown Role",
            "company": company or "Unknown Company",
            "link": link or "",
            "jobDescription": description or "No Description Available",
            "scrapedAt": datetime.utcnow().isoformat() + "Z",
            "platform": self.platform_name,
        }
