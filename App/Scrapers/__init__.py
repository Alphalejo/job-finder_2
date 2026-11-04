"""
scrapers package: platform-specific scrapers and base classes.
"""

from .base import BaseScraper
from .computrabajo import ComputrabajoScraper
from .elempleo import ElEmpleoScraper
from .getonboard import GetOnBoardScraper
from .glassdoor import GlassdoorScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .magneto import MagnetoScraper
from .torre import TorreScraper

SCRAPER_REGISTRY = {
    "linkedin": LinkedInScraper,
    "computrabajo": ComputrabajoScraper,
    "indeed": IndeedScraper,
    "elempleo": ElEmpleoScraper,
    "magneto365": MagnetoScraper,
    "getonboard": GetOnBoardScraper,
    "torre": TorreScraper,
    "glassdoor": GlassdoorScraper,
}

__all__ = [
    "BaseScraper",
    "SCRAPER_REGISTRY",
    "LinkedInScraper",
    "ComputrabajoScraper",
    "IndeedScraper",
    "ElEmpleoScraper",
    "MagnetoScraper",
    "GetOnBoardScraper",
    "TorreScraper",
    "GlassdoorScraper",
]
