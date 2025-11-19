from typing import List, Dict, Optional, Tuple
from django.core.paginator import Paginator
from django.db.models import Q

# Import vendor product models from db_pricing
from db_pricing.models import (
    GemilangProduct,
    Mitra10Product,
    DepoBangunanProduct,
    JuraganMaterialProduct,
    TokopediaProduct,
)

from .repositories.pricing_repository import PricingRepository


class VendorPricingService:
    """Service that returns a unified list of vendor product prices from the DB.

    This service isolates the dashboard from vendor-specific models and provides
    simple filtering, sorting and pagination. It intentionally avoids any
    scraping or network I/O.
    """

    VENDOR_SPECS = [
        (GemilangProduct, "Gemilang Store"),
        (DepoBangunanProduct, "Depo Bangunan"),
        (JuraganMaterialProduct, "Juragan Material"),
        (Mitra10Product, "Mitra10"),
        (TokopediaProduct, "Tokopedia"),
    ]

    def __init__(self, per_vendor_limit: int = 10000):
        # increase default per-vendor limit so `list_all_prices` returns a
        # comprehensive dataset unless caller supplies a smaller limit.
        self.per_vendor_limit = per_vendor_limit
        # Repository that performs combined SQL queries across vendor tables
        self.repository = PricingRepository(self.VENDOR_SPECS)

    def _query_vendor(self, model, source_name: str, q: Optional[str] = None) -> List[Dict]:
        qs = model.objects.all().order_by('-updated_at')
        if q:
            # search name and category
            qs = qs.filter(Q(name__icontains=q) | Q(category__icontains=q))

        items = []
        for p in qs[: self.per_vendor_limit]:
            items.append(
                {
                    "item": getattr(p, "name", ""),
                    "value": int(getattr(p, "price", 0) or 0),
                    "unit": getattr(p, "unit", ""),
                    "source": source_name,
                    "url": getattr(p, "url", ""),
                    "location": getattr(p, "location", ""),
                    "category": getattr(p, "category", "") or "Lainnya",
                    "created_at": getattr(p, "created_at", None),
                }
            )

        return items

    def list_prices(
        self, q: Optional[str] = None, page: int = 1, per_page: int = 20
    ) -> Tuple[List[Dict], int]:
        """Return combined vendor prices, optionally filtered by `q`, paginated.

        Returns (items_on_page, total_items)
        """
        # Use repository to fetch combined rows via a single SQL UNION query.
        try:
            # simplified repository call: fetch recent rows from all vendors
            combined = self.repository.fetch_all(per_vendor_limit=self.per_vendor_limit)
        except Exception:
            # Fallback: query vendors individually (safer but slower)
            combined = []
            for model, source in self.VENDOR_SPECS:
                try:
                    combined.extend(self._query_vendor(model, source, q=q))
                except Exception:
                    continue

        # simple dedupe by (source, url, item, value)
        seen = set()
        uniq = []
        for p in combined:
            key = (p.get("source"), p.get("url"), p.get("item"), p.get("value"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)

        # sort by price ascending by default
        uniq.sort(key=lambda x: x.get("value") or 0)

        paginator = Paginator(uniq, per_page)
        total = paginator.count
        try:
            page_obj = paginator.page(page)
            return list(page_obj.object_list), total
        except Exception:
            return [], total

    def list_all_prices(self, q: Optional[str] = None, per_vendor_limit: Optional[int] = None) -> List[Dict]:
        """Return the full combined, deduplicated and sorted list of prices.

        This is intended for templates that perform client-side filtering/pagination
        and therefore need the complete dataset rendered on the page.
        """
        if per_vendor_limit is None:
            per_vendor_limit = self.per_vendor_limit or 10000

        try:
            combined = self.repository.fetch_all(per_vendor_limit=per_vendor_limit)
        except Exception:
            combined = []
            for model, source in self.VENDOR_SPECS:
                try:
                    combined.extend(self._query_vendor(model, source, q=q))
                except Exception:
                    continue

        # dedupe & sort (same logic as list_prices)
        seen = set()
        uniq = []
        for p in combined:
            key = (p.get("source"), p.get("url"), p.get("item"), p.get("value"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)

        uniq.sort(key=lambda x: x.get("value") or 0)
        return uniq
