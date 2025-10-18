from urllib.parse import urljoin, quote
from api.core import BaseUrlBuilder
from api.interfaces import UrlBuilderError
from api.config import config


class BlibliUrlBuilder(BaseUrlBuilder):
    """
    Builds Blibli search URLs:
    - Path: /cari/{ITEM}
    - Params:
      - category=BA-1000038 (Bahan Bangunan)
      - sort: '3' (cheapest first) when sort_by_price=True, otherwise '0' (default relevance)
      - intent=false
      - firstLoad=false
      - page: 1-based (page+1)
      - start: 0-based offset (page*40) – Page size is 40 items
    """

    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or config.blibli_base_url,
            search_path or config.blibli_search_path,
        )

    def build_search_url(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> str:
        # Override to place keyword in the path segment (/cari/{keyword})
        if not keyword or not keyword.strip():
            raise UrlBuilderError("Keyword cannot be empty")
        if page < 0:
            raise UrlBuilderError("Page number cannot be negative")

        kw = quote(keyword.strip())
        # Ensure trailing slash so the keyword is appended correctly
        path = self.search_path if self.search_path.endswith("/") else f"{self.search_path}/"
        full_path = urljoin(self.base_url, f"{path}{kw}")

        # Reuse BaseUrlBuilder’s param builder to keep logging behavior consistent
        params = self._build_params(keyword.strip(), sort_by_price, page)

        from urllib.parse import urlencode
        return f"{full_path}?{urlencode(params)}"

    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        params = {
            "category": "BA-1000038", 
            "intent": "false",
            "firstLoad": "false",
            "page": page + 1,         # Blibli uses 1-based page indexing
            "start": page * 40,       # Page size is 40 items
        }
        params["sort"] = "3" if sort_by_price else "0"
        return params