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