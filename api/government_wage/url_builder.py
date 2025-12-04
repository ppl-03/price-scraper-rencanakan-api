from api.core import BaseUrlBuilder

class GovernmentWageUrlBuilder(BaseUrlBuilder):
    """
    URL builder for Government Wage (MasPetruk HSPK) scraper.
    
    Note: This scraper uses browser automation (Playwright) to handle region selection
    and search filtering, so URL parameters are not used. The URL is always the same
    base page, and interactions are handled via JavaScript/DOM manipulation.
    """
    
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or "https://maspetruk.dpubinmarcipka.jatengprov.go.id",
            search_path or "/harga_satuan/hspk"
        )

    def build_search_url(self, keyword: str = None, sort_by_price: bool = True, page: int = 0) -> str:
        return f"{self.base_url}{self.search_path}"

    def build_region_url(self) -> str:
        return self.build_search_url()
