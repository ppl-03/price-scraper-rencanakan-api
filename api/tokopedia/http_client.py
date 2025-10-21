"""
Tokopedia-specific HTTP client with optimized headers for better compatibility.
This client adds Tokopedia-specific headers to improve scraping success rate,
especially important when running in cloud environments like Azure.
"""

from api.core import BaseHttpClient
from api.config import config
import logging

logger = logging.getLogger(__name__)


class TokopediaHttpClient(BaseHttpClient):
    """
    HTTP client optimized for Tokopedia with specific headers.
    
    This client extends BaseHttpClient with Tokopedia-specific headers
    that help avoid anti-bot detection, especially important when
    scraping from cloud environments (Azure, AWS, etc.) where IPs
    may be more aggressively filtered.
    """
    
    def __init__(self, user_agent: str = None, max_retries: int = None, retry_delay: float = None):
        super().__init__(user_agent, max_retries, retry_delay)
        
        # Add Tokopedia-specific headers for better compatibility
        self.session.headers.update({
            'Referer': 'https://www.tokopedia.com/',
            'Origin': 'https://www.tokopedia.com',
        })
        
        logger.debug("TokopediaHttpClient initialized with enhanced headers")
    
    def get(self, url: str, timeout: int = None) -> str:
        """
        Override to add Tokopedia-specific logging and error handling.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            HTML content as string
        """
        logger.debug(f"TokopediaHttpClient fetching: {url}")
        return super().get(url, timeout)
