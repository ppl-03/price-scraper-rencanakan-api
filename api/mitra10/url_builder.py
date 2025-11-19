from api.core import BaseUrlBuilder
from api.config import config


class Mitra10UrlBuilder(BaseUrlBuilder):
    
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or config.mitra10_base_url,
            search_path or config.mitra10_search_path
        )
    
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {
            'q': keyword
        }
        
        if sort_by_price:
            # Provide the raw JSON string - urlencode() will handle the encoding
            params['sort'] = '{"key":"price","value":"ASC"}'
        else:
            # Sort by relevance/popularity in descending order (most relevant first)
            params['sort'] = '{"key":"relevance","value":"DESC"}'
        
        # Add page parameter (Mitra10 uses 1-based pagination)
        params['page'] = page + 1
        
        return params