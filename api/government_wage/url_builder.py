from api.core import BaseUrlBuilder

class GovernmentWageUrlBuilder(BaseUrlBuilder):
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or "https://maspetruk.dpubinmarcipka.jatengprov.go.id",
            search_path or "/harga_satuan/hspk"
        )

    def build_search_url(self, keyword: str = None, sort_by_price: bool = True, page: int = 0) -> str:
        url = f"{self.base_url}{self.search_path}"
        return url  

    def build_region_url(self, region: str = "Kab. Cilacap") -> str:
        return self.build_search_url()
