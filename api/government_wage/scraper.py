import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from api.core import BaseUrlBuilder
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, HttpClientError

from api.government_wage.gov_playwright_client import GovernmentWagePlaywrightClient

from api.government_wage.url_builder import GovernmentWageUrlBuilder
from api.government_wage.html_parser import GovernmentWageHtmlParser

logger = logging.getLogger(__name__)


@dataclass
class GovernmentWageItem:
    item_number: str
    work_code: str
    work_description: str
    unit: str
    unit_price_idr: int
    region: str
    edition: str = "Edisi Ke - 2"
    year: str = "2024"
    sector: str = "Bidang Cipta Karya dan Perumahan"


class GovernmentWageScraper:
    # Default region constant
    DEFAULT_REGION = "Kab. Cilacap"
    
    def __init__(
        self,
        http_client: Optional[IHttpClient] = None,
        url_builder: Optional[IUrlBuilder] = None,
        html_parser: Optional[IHtmlParser] = None,
    ):
        self.http_client = http_client or GovernmentWagePlaywrightClient()
        self.url_builder = url_builder or GovernmentWageUrlBuilder()
        self.html_parser = html_parser or GovernmentWageHtmlParser()

        # Central Java regions from DHSP Analysis
        self.available_regions = [
            self.DEFAULT_REGION, "Kab. Banyumas", "Kab. Purbalingga", "Kab. Banjarnegara",
            "Kab. Kebumen", "Kab. Purworejo", "Kab. Wonosobo", "Kab. Magelang",
            "Kab. Boyolali", "Kab. Klaten", "Kab. Sukoharjo", "Kab. Wonogiri",
            "Kab. Karanganyar", "Kab. Sragen", "Kab. Grobogan", "Kab. Blora",
            "Kab. Rembang", "Kab. Pati", "Kab. Kudus", "Kab. Jepara",
            "Kab. Demak", "Kab. Semarang", "Kab. Temanggung", "Kab. Kendal",
            "Kab. Batang", "Kab. Pekalongan", "Kab. Pemalang", "Kab. Tegal",
            "Kab. Brebes", "Kota Magelang", "Kota Surakarta", "Kota Salatiga",
            "Kota Semarang", "Kota Pekalongan", "Kota Tegal"
        ]

    def scrape_region_data(self, region: str = None) -> List[GovernmentWageItem]:
        if region is None:
            region = self.DEFAULT_REGION
        try:
            logger.info(f"Scraping government wage data for region: {region}")

            url = self.url_builder.build_search_url(region)

            if hasattr(self.http_client, "region_label"):
                self.http_client.region_label = region
            if hasattr(self.http_client, "auto_select_region"):
                self.http_client.auto_select_region = True

            html_content = self.http_client.get(url)

            if hasattr(self.html_parser, "parse_government_wage_data"):
                items = self.html_parser.parse_government_wage_data(html_content, region)
            else:
                products = self.html_parser.parse_products(html_content)
                items = [self._convert_product_to_wage_item(p, region) for p in products]

            logger.info(f"Successfully scraped {len(items)} items from {region}")
            return items

        except Exception as e:
            logger.error(f"Error scraping region {region}: {e}")
            return []


    def scrape_all_regions(self, max_regions: Optional[int] = None) -> List[GovernmentWageItem]:
        all_items = []
        regions_to_scrape = self.available_regions[:max_regions] if max_regions else self.available_regions

        logger.info(f"Starting to scrape {len(regions_to_scrape)} regions")

        for i, region in enumerate(regions_to_scrape, 1):
            try:
                logger.info(f"Scraping region {i}/{len(regions_to_scrape)}: {region}")
                items = self.scrape_region_data(region)
                all_items.extend(items)

                if i < len(regions_to_scrape):
                    time.sleep(5.0)

            except Exception as e:
                logger.error(f"Error scraping region {region}: {e}")
                continue

        logger.info(f"Completed scraping all regions. Total items: {len(all_items)}")
        return all_items

    def search_by_work_code(self, work_code: str, region: Optional[str] = None) -> List[GovernmentWageItem]:
        try:
            logger.info(f"Searching for work code: {work_code}")

            if region:
                return self._search_in_region(work_code, region)

            items = self._search_in_region(work_code, self.DEFAULT_REGION)
            filtered_items = [item for item in items if work_code.lower() in item.work_code.lower()]
            logger.info(f"Found {len(filtered_items)} items matching work code {work_code}")
            return filtered_items

        except Exception as e:
            logger.error(f"Error searching for work code {work_code}: {e}")
            return []

    def _search_in_region(self, work_code: str, region: str) -> List[GovernmentWageItem]:
        url = self.url_builder.build_search_url(work_code)
        html_content = self.http_client.get(url)

        if hasattr(self.html_parser, "parse_government_wage_data"):
            return self.html_parser.parse_government_wage_data(html_content, region)
        else:
            products = self.html_parser.parse_products(html_content)
            return [self._convert_product_to_wage_item(p, region) for p in products]

    def get_available_regions(self) -> List[str]:
        return self.available_regions.copy()

    def _convert_product_to_wage_item(self, product: Dict[str, Any], region: str) -> GovernmentWageItem:
        return GovernmentWageItem(
            item_number=product.get('item_number', ''),
            work_code=product.get('work_code', ''),
            work_description=product.get('work_description') or product.get('name', ''),
            unit=product.get('unit', ''),
            unit_price_idr=product.get('price', 0),
            region=region
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.http_client, 'close'):
            try:
                self.http_client.close()
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")


def create_government_wage_scraper(headless: bool = True, browser_type: str = "chromium") -> GovernmentWageScraper:
    http_client = GovernmentWagePlaywrightClient(headless=headless, browser_type=browser_type)
    url_builder = GovernmentWageUrlBuilder()
    html_parser = GovernmentWageHtmlParser()
    return GovernmentWageScraper(http_client, url_builder, html_parser)