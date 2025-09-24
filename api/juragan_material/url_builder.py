from api.core import BaseUrlBuilder


class JuraganMaterialUrlBuilder(BaseUrlBuilder):
    """URL builder for Juragan Material website."""
    
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or "https://juraganmaterial.id",
            search_path or "/produk"
        )
    
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        """
        Build query parameters for Juragan Material search.
        
        Args:
            keyword: Search keyword
            sort_by_price: Whether to sort by lowest price
            page: Page number (0-based, will be converted to 1-based)
            
        Returns:
            dict: Query parameters for the URL
        """
        params = {
            'keyword': keyword,
            'page': page + 1  # JuraganMaterial uses 1-based pagination
        }
        
        if sort_by_price:
            params['sort'] = 'lowest_price'
        else:
            params['sort'] = 'relevance'
        
        return params