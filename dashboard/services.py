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
from .category_validators import CategoryUpdateRequestValidator


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


class CategoryUpdateService:
    """Service responsible for updating product categories across vendor models.
    
    This service follows the Single Responsibility Principle by focusing solely on
    category update operations. It handles validation, model lookup, and update logic
    in a clean, testable way.
    """

    # Map source names to their respective models
    VENDOR_MODEL_MAP = {
        "Gemilang Store": GemilangProduct,
        "Depo Bangunan": DepoBangunanProduct,
        "Juragan Material": JuraganMaterialProduct,
        "Mitra10": Mitra10Product,
        "Tokopedia": TokopediaProduct,
    }

    def __init__(self, validator: Optional[CategoryUpdateRequestValidator] = None):
        """Initialize the category update service.
        
        Args:
            validator: Optional custom validator instance (for testing/customization)
        """
        self.validator = validator or CategoryUpdateRequestValidator()

    def update_category(self, source: str, product_url: str, new_category: str) -> Dict:
        """Update the category of a specific product.
        
        Args:
            source: The vendor source name (e.g., "Gemilang Store")
            product_url: The URL of the product to update
            new_category: The new category value to set
            
        Returns:
            Dict containing success status and message, or error information
            
        Raises:
            ValueError: If source is invalid or product not found
        """
        # Validate inputs using the validator
        validation_result = self.validator.validate_update_request(
            source, product_url, new_category
        )
        
        if not validation_result.get("valid"):
            return {
                "success": False,
                "error": validation_result.get("error", "Validation failed")
            }
        
        # Get the model for this vendor
        model = self.VENDOR_MODEL_MAP.get(source)
        if not model:
            return {
                "success": False,
                "error": f"Invalid vendor source: {source}"
            }
        
        # Find the product by URL (unique identifier across vendors)
        try:
            product = model.objects.get(url=product_url)
        except model.DoesNotExist:
            return {
                "success": False,
                "error": f"Product not found with URL: {product_url}"
            }
        
        # Store old category for logging/auditing
        old_category = product.category
        
        # Update the category
        product.category = new_category.strip()
        product.save(update_fields=['category', 'updated_at'])
        
        return {
            "success": True,
            "message": "Category updated successfully",
            "product_name": product.name,
            "old_category": old_category,
            "new_category": product.category,
            "vendor": source,
            "updated_at": product.updated_at.isoformat()
        }
    
    def bulk_update_categories(self, updates: List[Dict]) -> Dict:
        """Update multiple product categories in a single operation.
        
        Args:
            updates: List of dicts with keys: source, product_url, new_category
            
        Returns:
            Dict with success count, failure count, and detailed results
        """
        # Validate the entire bulk request first
        bulk_validation = self.validator.validate_bulk_request(updates)
        
        if not bulk_validation.get("valid"):
            return {
                "success": False,
                "error": bulk_validation.get("error"),
                "validation_errors": bulk_validation.get("errors", []),
                "success_count": 0,
                "failure_count": len(updates)
            }
        
        results = {
            "success_count": 0,
            "failure_count": 0,
            "updates": []
        }
        
        for update_data in updates:
            source = update_data.get("source")
            product_url = update_data.get("product_url")
            new_category = update_data.get("new_category")
            
            result = self.update_category(source, product_url, new_category)
            
            if result.get("success"):
                results["success_count"] += 1
            else:
                results["failure_count"] += 1
            
            results["updates"].append(result)
        
        return results
    
    def get_available_vendors(self) -> List[str]:
        """Get list of available vendor sources.
        
        Returns:
            List of vendor source names
        """
        return list(self.VENDOR_MODEL_MAP.keys())
