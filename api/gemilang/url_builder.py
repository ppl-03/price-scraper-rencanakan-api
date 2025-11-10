from api.core import BaseUrlBuilder
from api.config import config


class GemilangUrlBuilder(BaseUrlBuilder):
    
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or config.gemilang_base_url,
            search_path or config.gemilang_search_path
        )
    
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {
            'keyword': keyword,
            'page': page
        }
        
        if sort_by_price:
            params['sort'] = 'price_asc'
        else:
            None  # No sorting parameter added because Gemilang does not have popularity filter or rating options
        
        return params