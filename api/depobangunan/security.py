import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# A04:2021 – Insecure Design Prevention
# =============================================================================

class SecurityDesignPatterns:
    """
    Implements secure design patterns and best practices.
    Implements OWASP A04:2021 - Use secure design patterns.
    """
    
    @staticmethod
    def _validate_price_field(price: Any) -> Tuple[bool, str]:
        """Validate price field in business logic."""
        if not isinstance(price, (int, float)) or price < 0:
            return False, "Price must be a positive number"
        if price > 1000000000:
            logger.warning(f"Suspicious price value: {price}")
            return False, "Price value exceeds reasonable limit"
        return True, ""
    
    @staticmethod
    def _validate_name_field(name: str) -> Tuple[bool, str]:
        """Validate name field in business logic."""
        if len(name) > 500:
            return False, "Product name too long"
        if len(name) < 2:
            return False, "Product name too short"
        return True, ""
    
    @staticmethod
    def _validate_url_field(url: str) -> Tuple[bool, str]:
        """Validate URL field with SSRF protection."""
        if not url.startswith('https://'):
            return False, "URL must use HTTPS protocol for security"
        if 'localhost' in url or '127.0.0.1' in url or '0.0.0.0' in url:
            logger.critical(f"SSRF attempt detected: {url}")
            return False, "Invalid URL"
        return True, ""
    
    @staticmethod
    def validate_business_logic(data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate business logic constraints.
        Implements plausibility checks.
        """
        if 'price' in data:
            is_valid, error_msg = SecurityDesignPatterns._validate_price_field(data['price'])
            if not is_valid:
                return False, error_msg
        
        if 'name' in data:
            is_valid, error_msg = SecurityDesignPatterns._validate_name_field(data['name'])
            if not is_valid:
                return False, error_msg
        
        if 'url' in data:
            is_valid, error_msg = SecurityDesignPatterns._validate_url_field(data['url'])
            if not is_valid:
                return False, error_msg
        
        return True, ""
    
    @staticmethod
    def enforce_resource_limits(request, max_page_size: int = 100) -> Tuple[bool, str]:
        """
        Enforce resource consumption limits.
        Implements OWASP A04:2021 - Limit resource consumption.
        """
        # Limit page size
        if 'limit' in request.GET:
            try:
                limit = int(request.GET['limit'])
                if limit > max_page_size:
                    return False, f"Limit exceeds maximum of {max_page_size}"
            except ValueError:
                return False, "Invalid limit parameter"
        
        # Limit query complexity
        query_params_count = len(request.GET)
        if query_params_count > 20:
            logger.warning(f"Excessive query parameters: {query_params_count}")
            return False, "Too many query parameters"
        
        return True, ""
