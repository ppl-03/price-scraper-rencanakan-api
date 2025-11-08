from .url_builder import TokopediaUrlBuilder
from typing import Union, List


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

        # For the 'ulasan' builder, when the caller passes sort_by_price=False
        # we explicitly request ob=5 (popularity/reviews). When sort_by_price is
        # True we keep the parent's behavior (ob=3).
        if not sort_by_price:
            params["ob"] = "5"

        return params
