import logging
import warnings
from typing import List, Optional
from api.core import BasePriceScraper, BaseHttpClient
from api.interfaces import IHttpClient, IUrlBuilder, IHtmlParser, Product, ScrapingResult
from api.playwright_client import BatchPlaywrightClient
from .url_builder import TokopediaUrlBuilder
from .html_parser import TokopediaHtmlParser
from .price_cleaner import TokopediaPriceCleaner

# Configure logger for this module
logger = logging.getLogger(__name__)


class TokopediaLocationError(ValueError):
    """Raised when an invalid location is specified for Tokopedia scraping."""
    pass


class TokopediaScrapingError(Exception):
    """Base exception for Tokopedia scraping errors."""
    pass


class TokopediaPriceScraper(BasePriceScraper):
    
    def __init__(self, http_client: IHttpClient = None, url_builder: IUrlBuilder = None, 
                 html_parser: IHtmlParser = None):
        # Use Tokopedia-specific components if not provided
        self.url_builder = url_builder or TokopediaUrlBuilder()
        self.html_parser = html_parser or TokopediaHtmlParser()
        
        # Use BaseHttpClient as default since Playwright has HTTP/2 issues with Tokopedia
        if http_client is None:
            http_client = BaseHttpClient()
            
        super().__init__(http_client, self.url_builder, self.html_parser)
    
    def _validate_and_get_location_ids(self, location: str) -> Optional[List[int]]:
        """
        Helper method to validate location and get location IDs with proper warning handling.
        
        Args:
            location: Location name to validate
            
        Returns:
            List of location IDs if location is valid, None if invalid or not found
        """
        if not location:
            return None
            
        location_ids = get_location_ids(location)
        if not location_ids:
            available_locations = list(TOKOPEDIA_LOCATION_IDS.keys())
            # Do not log user-controlled data to prevent log injection attacks
            warning_msg = f"Unknown location provided. Available locations: {available_locations}"
            logger.warning(warning_msg)
            warnings.warn(warning_msg, UserWarning, stacklevel=3)
            
        return location_ids
    
    def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0, 
                       limit: Optional[int] = None) -> ScrapingResult:
        """
        Override base method to add limit support
        
        Args:
            keyword: Search term (e.g., "semen")
            sort_by_price: Whether to sort by lowest price (default: True)
            page: Page number (0-based, default: 0)
            limit: Maximum number of products to return (will fetch multiple pages if needed)
            
        Returns:
            ScrapingResult with products and metadata
        """
        # Use scrape_products_with_filters with limit support
        return self.scrape_products_with_filters(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page,
            min_price=None,
            max_price=None,
            location=None,
            limit=limit
        )
    
    def scrape_products_with_filters(self, keyword: str, sort_by_price: bool = True, 
                                   page: int = 0, min_price: Optional[int] = None, 
                                   max_price: Optional[int] = None,
                                   location: Optional[str] = None,
                                   limit: Optional[int] = None) -> ScrapingResult:
        """
        Scrape Tokopedia products with advanced filters
        
        Args:
            keyword: Search term (e.g., "semen")
            sort_by_price: Whether to sort by lowest price (default: True)
            page: Page number (0-based, default: 0)
            min_price: Minimum price filter in Rupiah (optional)
            max_price: Maximum price filter in Rupiah (optional)
            location: Location name (e.g., "jakarta", "bandung", "jabodetabek") (optional)
            limit: Maximum number of products to return (will fetch multiple pages if needed)
            
        Returns:
            ScrapingResult with products and metadata
        """
        try:
            # Get location IDs if location is specified
            location_ids = self._validate_and_get_location_ids(location)
            
            # If limit is specified, fetch multiple pages until we have enough products
            if limit and limit > 0:
                return self._scrape_with_limit(
                    keyword=keyword,
                    sort_by_price=sort_by_price,
                    start_page=page,
                    min_price=min_price,
                    max_price=max_price,
                    location_ids=location_ids,
                    limit=limit
                )
            
            # Build URL with filters using the enhanced URL builder
            url = self.url_builder.build_search_url_with_filters(
                keyword=keyword,
                sort_by_price=sort_by_price,
                page=page,
                min_price=min_price,
                max_price=max_price,
                location_ids=location_ids
            )
            
            # Use http_client directly (works with both BaseHttpClient and BatchPlaywrightClient)
            html_content = self.http_client.get(url)
            products = self.html_parser.parse_products(html_content)
            
            return ScrapingResult(
                products=products,
                success=True,
                url=url
            )
            
        except Exception as e:
            return ScrapingResult(
                products=[],
                success=False,
                error_message=str(e),
                url=None
            )
    
    def _scrape_with_limit(self, keyword: str, sort_by_price: bool, start_page: int,
                          min_price: Optional[int], max_price: Optional[int],
                          location_ids: Optional[List[int]], limit: int) -> ScrapingResult:
        """
        Scrape multiple pages until we have the desired number of products
        
        Args:
            keyword: Search term
            sort_by_price: Whether to sort by lowest price
            start_page: Starting page number
            min_price: Minimum price filter
            max_price: Maximum price filter
            location_ids: Location IDs filter
            limit: Maximum number of products to return
            
        Returns:
            ScrapingResult with collected products
        """
        all_products = []
        current_page = start_page
        max_pages = 10  # Safety limit to avoid infinite loops
        last_url = None
        
        while len(all_products) < limit and current_page < (start_page + max_pages):
            try:
                url = self.url_builder.build_search_url_with_filters(
                    keyword=keyword,
                    sort_by_price=sort_by_price,
                    page=current_page,
                    min_price=min_price,
                    max_price=max_price,
                    location_ids=location_ids
                )
                last_url = url
                
                html_content = self.http_client.get(url)
                products = self.html_parser.parse_products(html_content)
                
                # If no products found on this page, stop
                if not products:
                    logger.info(f"No more products found at page {current_page}")
                    break
                
                all_products.extend(products)
                logger.info(f"Fetched {len(products)} products from page {current_page}. Total: {len(all_products)}")
                
                current_page += 1
                
            except Exception as e:
                logger.error(f"Error fetching page {current_page}: {str(e)}")
                break
        
        # Trim to the exact limit
        if len(all_products) > limit:
            all_products = all_products[:limit]
        
        return ScrapingResult(
            products=all_products,
            success=True,
            url=last_url
        )
    
    def scrape_batch_with_filters(self, keywords: List[str], sort_by_price: bool = True,
                                min_price: Optional[int] = None, 
                                max_price: Optional[int] = None,
                                location: Optional[str] = None) -> List[Product]:
        """
        Scrape multiple keywords with filters in batch
        
        Args:
            keywords: List of search terms
            sort_by_price: Whether to sort by lowest price
            min_price: Minimum price filter in Rupiah (optional)
            max_price: Maximum price filter in Rupiah (optional)
            location: Location name (e.g., "jakarta", "bandung") (optional)
            
        Returns:
            List of all products found across all keywords
        """
        all_products = []
        
        # Get location IDs if location is specified
        location_ids = self._validate_and_get_location_ids(location)
        
        with BatchPlaywrightClient() as batch_client:
            for keyword in keywords:
                try:
                    url = self.url_builder.build_search_url_with_filters(
                        keyword=keyword,
                        sort_by_price=sort_by_price,
                        page=0,
                        min_price=min_price,
                        max_price=max_price,
                        location_ids=location_ids
                    )
                    
                    html_content = batch_client.get(url)
                    products = self.html_parser.parse_products(html_content)
                    all_products.extend(products)
                    
                except Exception as e:
                    # Do not log user-controlled data to prevent log injection attacks
                    error_msg = f"Error scraping keyword in batch: {e}"
                    logger.error(error_msg)
                    continue
        
        return all_products
    
    def scrape_batch(self, keywords: List[str]) -> List[Product]:
        """
        Override parent method to use BatchPlaywrightClient for better JavaScript support
        """
        return self.scrape_batch_with_filters(keywords)


# Tokopedia location IDs mapping (supports multiple IDs per region)
# To find more IDs: Use browser DevTools on tokopedia.com/search, apply location filters,
# and check the 'fcity' parameter in the Network tab
TOKOPEDIA_LOCATION_IDS = {
    # DKI Jakarta - all Jakarta areas
    'dki_jakarta': [174, 175, 176, 177, 178, 179],
    'jakarta': [174, 175, 176, 177, 178, 179],  # Alias for DKI Jakarta
    
    # Jabodetabek - Greater Jakarta area
    'jabodetabek': [144, 146, 150, 151, 167, 168, 171, 174, 175, 176, 177, 178, 179, 463],
    
    'bandung': [165],

    'medan': [46],

    'surabaya': [252],
}


def get_location_ids(location_name: str) -> List[int]:
    """
    Get location IDs for a given location name.
    
    Args:
        location_name: Name of the location (case-insensitive)
        
    Returns:
        List of location IDs, empty list if location not found
        
    Examples:
        get_location_ids('jakarta') -> [174, 175, 176, 177, 178, 179]
        get_location_ids('bandung') -> [165]
        get_location_ids('jabodetabek') -> [144, 146, 150, ...]
    """
    location_key = location_name.lower().replace(' ', '_')
    return TOKOPEDIA_LOCATION_IDS.get(location_key, [])


def get_location_ids_strict(location_name: str) -> List[int]:
    """
    Get location IDs for a given location name with strict error handling.
    
    Args:
        location_name: Name of the location (case-insensitive)
        
    Returns:
        List of location IDs
        
    Raises:
        TokopediaLocationError: If the location is not found
        
    Examples:
        get_location_ids_strict('jakarta') -> [174, 175, 176, 177, 178, 179]
        get_location_ids_strict('invalid') -> raises TokopediaLocationError
    """
    location_key = location_name.lower().replace(' ', '_')
    location_ids = TOKOPEDIA_LOCATION_IDS.get(location_key)
    
    if not location_ids:
        available_locations = list(TOKOPEDIA_LOCATION_IDS.keys())
        raise TokopediaLocationError(
            f"Unknown location '{location_name}'. Available locations: {available_locations}"
        )
    
    return location_ids


def get_available_locations() -> List[str]:
    """
    Get list of all available location names.
    
    Returns:
        List of available location names
    """
    return list(TOKOPEDIA_LOCATION_IDS.keys())