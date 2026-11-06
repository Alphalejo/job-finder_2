"""
scrapers package: platform-specific scrapers and base classes.
"""

from .base import BaseScraper
from .computrabajo import ComputrabajoScraper
from .elempleo import ElEmpleoScraper
from .getonboard import GetOnBoardScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper

SCRAPER_REGISTRY = {
    "linkedin": LinkedInScraper,
    "computrabajo": ComputrabajoScraper,
    "indeed": IndeedScraper,
    "elempleo": ElEmpleoScraper,
    "getonboard": GetOnBoardScraper,

}

__all__ = [
    "BaseScraper",
    "SCRAPER_REGISTRY",
    "LinkedInScraper",
    "ComputrabajoScraper",
    "IndeedScraper",
    "ElEmpleoScraper",
    "GetOnBoardScraper",

]
