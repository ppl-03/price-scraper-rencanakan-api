from api.tokopedia_core import BaseUrlBuilder
from urllib.parse import urlencode, urljoin
from typing import List, Union


class TokopediaUrlBuilderUlasan(BaseUrlBuilder):
    """Build Tokopedia category/search URLs sorted by "ulasan" (reviews/popularity).

    This mirrors the interface of `TokopediaUrlBuilder` in `url_builder.py` but
    sets the `ob` parameter to '5' when `sort_by_ulasan` is True.
    """

    def __init__(self, base_url: str = None, search_path: str = None):
        super().__init__(
            base_url or "https://www.tokopedia.com",
            search_path or "/p/pertukangan/material-bangunan"
        )

    def _build_params(self, keyword: str, sort_by_price: bool, page: int) -> dict:
        """
        Build query params. This builder is compatible with the
        TokopediaPriceScraper which passes the `sort_by_price` keyword.

        When `sort_by_price` is False this builder will set `ob=5` to
        request sorting by "ulasan" (popularity/reviews).
        """
        params = {
            'q': keyword
        }

        # The default scraper uses a boolean `sort_by_price` flag. For
        # this ulasan builder, a False value indicates we want the
        # popularity/reviews ordering (ob=5).
        if not sort_by_price:
            params['ob'] = '5'  # Sort by "ulasan" / popularity / reviews

        # Add page parameter (Tokopedia uses 1-based pagination)
        if page > 0:
            params['page'] = page + 1

        return params

    def _add_price_filters(self, params: dict, min_price: int, max_price: int) -> None:
        """Add price range filters to params"""
        if min_price is not None and min_price > 0:
            params['pmin'] = min_price

        if max_price is not None and max_price > 0:
            params['pmax'] = max_price

    def _add_location_filter(self, params: dict, location_ids: Union[int, List[int]]) -> None:
        """Add location filter to params - handle both single ID and multiple IDs"""
        if location_ids is None:
            return

        if isinstance(location_ids, list):
            if location_ids:  # Not empty list
                params['fcity'] = ','.join(map(str, location_ids))
        elif isinstance(location_ids, int) and location_ids > 0:
            params['fcity'] = location_ids

    def build_search_url_with_filters(self, keyword: str, sort_by_price: bool = True,
                                      page: int = 0, min_price: int = None, max_price: int = None,
                                      location_ids: Union[int, List[int]] = None) -> str:
        """
        Build URL with additional filters for price range and location, sorted by ulasan if requested.

        Args:
            keyword: Search term
            sort_by_ulasan: Whether to sort by "ulasan" (reviews/popularity)
            page: Page number (0-based)
            min_price: Minimum price filter
            max_price: Maximum price filter
            location_ids: City/location ID filter (single int or list of ints)
        """
        try:
            if not keyword or not keyword.strip():
                raise ValueError("Keyword cannot be empty")

            if page < 0:
                raise ValueError("Page number cannot be negative")

            # Keep the same keyword name used by the scraper (`sort_by_price`)
            params = self._build_params(keyword.strip(), sort_by_price, page)

            # Add price and location filters using helper methods
            self._add_price_filters(params, min_price, max_price)
            self._add_location_filter(params, location_ids)

            # Build the full URL
            full_url = urljoin(self.base_url, self.search_path)
            url = f"{full_url}?{urlencode(params)}"

            return url

        except Exception as e:
            raise ValueError(f"Failed to build URL: {str(e)}")
