import asyncio
import time
import re
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from bs4 import BeautifulSoup

from api.core import BaseHttpClient, BaseUrlBuilder
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, HttpClientError
from api.playwright_client import PlaywrightHttpClient

logger = logging.getLogger(__name__)


@dataclass
class GovernmentWageItem:
    """Data model for government wage/HSPK items based on DHSP Analysis"""
    item_number: str
    work_code: str
    work_description: str
    unit: str
    unit_price_idr: int
    region: str
    edition: str = "Edisi Ke - 2"
    year: str = "2024"
    sector: str = "Bidang Cipta Karya dan Perumahan"


class GovernmentWageUrlBuilder(BaseUrlBuilder):
    """URL builder for MAS PETRUK government wage system"""
    
    def __init__(self):
        base_url = "https://maspetruk.dpubinmarcipka.jatengprov.go.id"
        search_path = "/harga_satuan/hspk"
        super().__init__(base_url, search_path)
    
    def build_search_url(self, keyword: str = None, sort_by_price: bool = True, page: int = 0) -> str:
        """Build URL for government wage data"""
        try:
            # Base URL for HSPK data
            url = f"{self.base_url}{self.search_path}"
            
            # Add fragment identifier as seen in DHSP analysis
            if keyword:
                url += f"#{keyword}"
            else:
                url += "#"
            
            logger.debug(f"Built government wage URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error building URL for keyword '{keyword}': {e}")
            raise HttpClientError(f"Failed to build URL: {e}")
    
    def build_region_url(self, region: str = "Kab. Cilacap") -> str:
        """Build URL for specific region data"""
        return self.build_search_url(region)


class GovernmentWageHtmlParser(IHtmlParser):
    """HTML parser for MAS PETRUK government wage data"""
    
    def parse_products(self, html_content: str) -> List[Any]:
        """Parse products - compatibility method for interface"""
        # Convert GovernmentWageItem to generic products if needed
        items = self.parse_government_wage_data(html_content)
        return [self._convert_to_product(item) for item in items]
    
    def parse_government_wage_data(self, html_content: str, region: str = "Unknown") -> List[GovernmentWageItem]:
        """Parse government wage data from HTML content following DHSP Analysis structure"""
        try:
            if not html_content or not html_content.strip():
                logger.warning("Empty HTML content received")
                return []
            
            # Check for common error states from DHSP Analysis
            if self._is_processing_state(html_content):
                logger.info("Content is in processing state (Sedang memproses...)")
                return []
            
            if self._is_no_data_state(html_content):
                logger.info("No data found (Tidak ditemukan data yang sesuai)")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the main data table as specified in DHSP Analysis
            # Path: table.dataTable -> tbody -> tr -> td
            data_table = soup.find('table', class_='dataTable')
            
            if not data_table:
                logger.warning("DataTable not found in HTML content")
                return []
            
            tbody = data_table.find('tbody')
            if not tbody:
                logger.warning("Table body not found in DataTable")
                return []
            
            rows = tbody.find_all('tr')
            if not rows:
                logger.info("No data rows found in table")
                return []
            
            items = []
            for row in rows:
                try:
                    item = self._parse_table_row(row, region)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.warning(f"Error parsing table row: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(items)} government wage items from {region}")
            return items
            
        except Exception as e:
            logger.error(f"Error parsing government wage HTML: {e}")
            return []
    
    def _parse_table_row(self, row, region: str) -> Optional[GovernmentWageItem]:
        """Parse individual table row based on DHSP Analysis column structure"""
        try:
            cells = row.find_all('td')
            
            if len(cells) < 5:
                logger.debug("Row has insufficient columns, skipping")
                return None
            
            # Column breakdown from DHSP Analysis:
            # td:nth-child(1) - Sequential number (No.)
            # td:nth-child(2) - Work item code (Kode)  
            # td:nth-child(3) - Work description (Uraian Pekerjaan)
            # td:nth-child(4) - Unit of measurement (Satuan)
            # td:nth-child(5) - Unit price in IDR (Harga Satuan)
            
            item_number = self._clean_text(cells[0].get_text())
            work_code = self._clean_text(cells[1].get_text())
            work_description = self._clean_text(cells[2].get_text())
            unit = self._clean_text(cells[3].get_text())
            price_text = self._clean_text(cells[4].get_text())
            
            # Clean and parse price
            unit_price = self._parse_price(price_text)
            
            # Validate required fields
            if not all([work_code, work_description, unit]):
                logger.debug("Missing required fields, skipping row")
                return None
            
            return GovernmentWageItem(
                item_number=item_number,
                work_code=work_code,
                work_description=work_description,
                unit=unit,
                unit_price_idr=unit_price,
                region=region
            )
            
        except Exception as e:
            logger.warning(f"Error parsing table row: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        return text.strip().replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    
    def _parse_price(self, price_text: str) -> int:
        """Parse price from Indonesian Rupiah format"""
        try:
            if not price_text:
                return 0
            
            # Remove common currency symbols and separators
            # Indonesian format often uses dots or commas as thousands separators
            cleaned = re.sub(r'[^\d]', '', price_text)
            
            if not cleaned:
                return 0
            
            return int(cleaned)
            
        except (ValueError, TypeError):
            logger.warning(f"Could not parse price: {price_text}")
            return 0
    
    def _is_processing_state(self, html_content: str) -> bool:
        """Check if content is in processing state"""
        return "Sedang memproses" in html_content or "Processing" in html_content
    
    def _is_no_data_state(self, html_content: str) -> bool:
        """Check if no data was found"""
        return "Tidak ditemukan data yang sesuai" in html_content or "No data found" in html_content
    
    def _convert_to_product(self, item: GovernmentWageItem) -> Dict[str, Any]:
        """Convert GovernmentWageItem to generic product format"""
        return {
            'name': f"{item.work_code} - {item.work_description}",
            'price': item.unit_price_idr,
            'url': f"https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk#{item.work_code}",
            'unit': item.unit,
            'work_code': item.work_code,
            'region': item.region
        }


class GovernmentWageHttpClient(PlaywrightHttpClient):
    """HTTP client optimized for government wage scraping with JavaScript support"""
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        super().__init__(headless, browser_type)
        self.government_delay = 3.0  # Respectful delay for government sites
    
    def get(self, url: str, timeout: int = 60) -> str:
        """Get content with government site optimizations"""
        try:
            # Add respectful delay before government site requests
            time.sleep(self.government_delay)
            
            logger.info(f"Fetching government wage data from: {url}")
            html_content = super().get(url, timeout)
            
            # Additional wait to ensure dynamic content loads
            time.sleep(2.0)
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error fetching government wage data: {e}")
            raise HttpClientError(f"Failed to fetch government data: {e}")


class GovernmentWageScraper:
    """Main scraper for Central Java government wage data (MAS PETRUK system)"""
    
    def __init__(self, 
                 http_client: Optional[IHttpClient] = None,
                 url_builder: Optional[IUrlBuilder] = None, 
                 html_parser: Optional[IHtmlParser] = None):
        self.http_client = http_client or GovernmentWageHttpClient()
        self.url_builder = url_builder or GovernmentWageUrlBuilder()
        self.html_parser = html_parser or GovernmentWageHtmlParser()
        
        # Central Java regions from DHSP Analysis
        self.available_regions = [
            "Kab. Cilacap", "Kab. Banyumas", "Kab. Purbalingga", "Kab. Banjarnegara",
            "Kab. Kebumen", "Kab. Purworejo", "Kab. Wonosobo", "Kab. Magelang",
            "Kab. Boyolali", "Kab. Klaten", "Kab. Sukoharjo", "Kab. Wonogiri",
            "Kab. Karanganyar", "Kab. Sragen", "Kab. Grobogan", "Kab. Blora",
            "Kab. Rembang", "Kab. Pati", "Kab. Kudus", "Kab. Jepara",
            "Kab. Demak", "Kab. Semarang", "Kab. Temanggung", "Kab. Kendal",
            "Kab. Batang", "Kab. Pekalongan", "Kab. Pemalang", "Kab. Tegal",
            "Kab. Brebes", "Kota Magelang", "Kota Surakarta", "Kota Salatiga",
            "Kota Semarang", "Kota Pekalongan", "Kota Tegal"
        ]
    
    def scrape_region_data(self, region: str = "Kab. Cilacap") -> List[GovernmentWageItem]:
        """Scrape government wage data for a specific region"""
        try:
            logger.info(f"Scraping government wage data for region: {region}")
            
            url = self.url_builder.build_search_url(region)
            html_content = self.http_client.get(url)
            
            if isinstance(self.html_parser, GovernmentWageHtmlParser):
                items = self.html_parser.parse_government_wage_data(html_content, region)
            else:
                # Fallback for generic parser
                products = self.html_parser.parse_products(html_content)
                items = [self._convert_product_to_wage_item(p, region) for p in products]
            
            logger.info(f"Successfully scraped {len(items)} items from {region}")
            return items
            
        except Exception as e:
            logger.error(f"Error scraping region {region}: {e}")
            return []
    
    def scrape_all_regions(self, max_regions: Optional[int] = None) -> List[GovernmentWageItem]:
        """Scrape data from all available regions in Central Java"""
        all_items = []
        regions_to_scrape = self.available_regions[:max_regions] if max_regions else self.available_regions
        
        logger.info(f"Starting to scrape {len(regions_to_scrape)} regions")
        
        for i, region in enumerate(regions_to_scrape, 1):
            try:
                logger.info(f"Scraping region {i}/{len(regions_to_scrape)}: {region}")
                items = self.scrape_region_data(region)
                all_items.extend(items)
                
                # Respectful delay between regions
                if i < len(regions_to_scrape):
                    time.sleep(5.0)
                    
            except Exception as e:
                logger.error(f"Error scraping region {region}: {e}")
                continue
        
        logger.info(f"Completed scraping all regions. Total items: {len(all_items)}")
        return all_items
    
    def search_by_work_code(self, work_code: str, region: Optional[str] = None) -> List[GovernmentWageItem]:
        """Search for specific work codes"""
        try:
            logger.info(f"Searching for work code: {work_code}")
            
            # If specific region provided, search in that region
            if region:
                return self._search_in_region(work_code, region)
            
            # Otherwise search in default region (Cilacap) or all regions
            items = self._search_in_region(work_code, "Kab. Cilacap")
            
            # Filter results by work code if needed
            filtered_items = [item for item in items if work_code.lower() in item.work_code.lower()]
            
            logger.info(f"Found {len(filtered_items)} items matching work code {work_code}")
            return filtered_items
            
        except Exception as e:
            logger.error(f"Error searching for work code {work_code}: {e}")
            return []
    
    def _search_in_region(self, work_code: str, region: str) -> List[GovernmentWageItem]:
        """Search for work code in specific region"""
        url = self.url_builder.build_search_url(work_code)
        html_content = self.http_client.get(url)
        
        if isinstance(self.html_parser, GovernmentWageHtmlParser):
            return self.html_parser.parse_government_wage_data(html_content, region)
        else:
            products = self.html_parser.parse_products(html_content)
            return [self._convert_product_to_wage_item(p, region) for p in products]
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions"""
        return self.available_regions.copy()
    
    def _convert_product_to_wage_item(self, product: Dict[str, Any], region: str) -> GovernmentWageItem:
        """Convert generic product to GovernmentWageItem"""
        return GovernmentWageItem(
            item_number="",
            work_code=product.get('work_code', ''),
            work_description=product.get('name', ''),
            unit=product.get('unit', ''),
            unit_price_idr=product.get('price', 0),
            region=region
        )
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        if hasattr(self.http_client, 'close'):
            try:
                self.http_client.close()
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")


# Factory function for easy instantiation
def create_government_wage_scraper(headless: bool = True, 
                                 browser_type: str = "chromium") -> GovernmentWageScraper:
    """Factory function to create a configured government wage scraper"""
    http_client = GovernmentWageHttpClient(headless=headless, browser_type=browser_type)
    url_builder = GovernmentWageUrlBuilder()
    html_parser = GovernmentWageHtmlParser()
    
    return GovernmentWageScraper(http_client, url_builder, html_parser)


# Example usage functions
def scrape_cilacap_data() -> List[GovernmentWageItem]:
    """Example: Scrape data for Cilacap region"""
    with create_government_wage_scraper() as scraper:
        return scraper.scrape_region_data("Kab. Cilacap")


def scrape_sample_regions(max_regions: int = 3) -> List[GovernmentWageItem]:
    """Example: Scrape data from first few regions for testing"""
    with create_government_wage_scraper() as scraper:
        return scraper.scrape_all_regions(max_regions=max_regions)


def search_construction_work(work_code_pattern: str = "A.1") -> List[GovernmentWageItem]:
    """Example: Search for construction work items"""
    with create_government_wage_scraper() as scraper:
        return scraper.search_by_work_code(work_code_pattern)