from api.core import BaseUrlBuilder
from api.config import config


class DepoUrlBuilder(BaseUrlBuilder):
    
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or config.depobangunan_base_url,
            search_path or config.depobangunan_search_path
        )
    
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {
            'q': keyword
        }
        
        if sort_by_price:
            params['product_list_order'] = 'low_to_high'
        
        return params
    
    def build_popularity_url(self, keyword: str, page: int = 0) -> str:
        """
        Build URL for popularity-sorted products (top rated)
        Example: https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=top_rated
        """
        params = {
            'q': keyword,
            'product_list_order': 'top_rated'
        }
        
        if page > 0:
            params['p'] = str(page)
        
        # Build URL
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url.rstrip('/')}/{self.search_path.strip('/')}?{param_str}"