from .url_builder import TokopediaUrlBuilder
from typing import Union, List
from typing import List, Union


class TokopediaUrlBuilderUlasan(TokopediaUrlBuilder):
    """Reuse `TokopediaUrlBuilder` for everything except the params-building.
    This subclass overrides only `_build_params` so it can request
    `ob=5` (popularity/ulasan) when the scraper signals it via
    `sort_by_price=False`. All other helpers and URL assembly are
    inherited from `TokopediaUrlBuilder`.
    """
    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or "https://www.tokopedia.com",
            search_path or "/p/pertukangan/material-bangunan",
        )
    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        # Start from the parent's params (keeps q, page and price-sort ob)
        params = super()._build_params(keyword, sort_by_price, page)

        # For the 'ulasan' builder the scraper uses the same boolean flag but
        # with inverted semantics compared to the price builder: a True value
        # here signals we want the 'ulasan' (popularity/reviews) ordering.
        # Therefore set ob=5 when sort_by_price is True.
        if sort_by_price:
            params["ob"] = "5"

        if page > 0:
            params['page'] = page + 1
        
        return params

    def build_search_url_with_filters(self, keyword: str, sort_by_price: bool = True,
                                      page: int = 0, min_price: int = None, max_price: int = None,
                                      location_ids: Union[int, List[int]] = None) -> str:
        """Compatibility wrapper: accept `sort_by_ulasan` keyword used by callers
        of this builder and forward to the parent implementation which expects
        `sort_by_price` (we map it accordingly).
        """
        # Map the ulasan flag into the parent's expected flag name
        return super().build_search_url_with_filters(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page,
            min_price=min_price,
            max_price=max_price,
            location_ids=location_ids,
        )