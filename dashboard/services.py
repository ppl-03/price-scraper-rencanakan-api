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
from .unit_validators import UnitUpdateRequestValidator

# Vendor name constants
VENDOR_GEMILANG = "Gemilang Store"
VENDOR_DEPO_BANGUNAN = "Depo Bangunan"
VENDOR_JURAGAN_MATERIAL = "Juragan Material"
VENDOR_MITRA10 = "Mitra10"
VENDOR_TOKOPEDIA = "Tokopedia"


class VendorPricingService:
    """Service that returns a unified list of vendor product prices from the DB.

    This service isolates the dashboard from vendor-specific models and provides
    simple filtering, sorting and pagination. It intentionally avoids any
    scraping or network I/O.
    """

    VENDOR_SPECS = [
        (GemilangProduct, VENDOR_GEMILANG),
        (DepoBangunanProduct, VENDOR_DEPO_BANGUNAN),
        (JuraganMaterialProduct, VENDOR_JURAGAN_MATERIAL),
        (Mitra10Product, VENDOR_MITRA10),
        (TokopediaProduct, VENDOR_TOKOPEDIA),
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

    def _fetch_combined_data(self, q: Optional[str], per_vendor_limit: int) -> List[Dict]:
        """Fetch combined data from all vendors with optional search filtering.
        
        Args:
            q: Optional search query
            per_vendor_limit: Maximum items per vendor
            
        Returns:
            List of combined product dictionaries
        """
        if q:
            return self._fetch_with_search(q)
        return self._fetch_without_search(per_vendor_limit, q)
    
    def _fetch_with_search(self, q: str) -> List[Dict]:
        """Fetch data using individual vendor queries with search filtering.
        
        Args:
            q: Search query string
            
        Returns:
            List of filtered products
        """
        combined = []
        for model, source in self.VENDOR_SPECS:
            try:
                combined.extend(self._query_vendor(model, source, q=q))
            except Exception:
                continue
        return combined
    
    def _fetch_without_search(self, per_vendor_limit: int, q: Optional[str]) -> List[Dict]:
        """Fetch data using repository fetch_all with fallback to individual queries.
        
        Args:
            per_vendor_limit: Maximum items per vendor
            q: Search query (used in fallback)
            
        Returns:
            List of products
        """
        try:
            return self.repository.fetch_all(per_vendor_limit=per_vendor_limit)
        except Exception:
            return self._fetch_fallback(q)
    
    def _fetch_fallback(self, q: Optional[str]) -> List[Dict]:
        """Fallback to individual vendor queries when repository fails.
        
        Args:
            q: Optional search query
            
        Returns:
            List of products from individual vendor queries
        """
        combined = []
        for model, source in self.VENDOR_SPECS:
            try:
                combined.extend(self._query_vendor(model, source, q=q))
            except Exception:
                continue
        return combined
    
    def _deduplicate_and_sort(self, combined: List[Dict]) -> List[Dict]:
        """Remove duplicates and sort by price.
        
        Args:
            combined: List of product dictionaries
            
        Returns:
            Deduplicated and sorted list
        """
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

    def list_all_prices(self, q: Optional[str] = None, per_vendor_limit: Optional[int] = None) -> List[Dict]:
        """Return the full combined, deduplicated and sorted list of prices.

        This is intended for templates that perform client-side filtering/pagination
        and therefore need the complete dataset rendered on the page.
        
        Args:
            q: Optional search query to filter by product name or category
            per_vendor_limit: Maximum items to fetch per vendor
        """
        if per_vendor_limit is None:
            per_vendor_limit = self.per_vendor_limit or 10000

        combined = self._fetch_combined_data(q, per_vendor_limit)
        return self._deduplicate_and_sort(combined)


class CategoryUpdateService:
    """Service responsible for updating product categories across vendor models.
    
    This service follows the Single Responsibility Principle by focusing solely on
    category update operations. It handles validation, model lookup, and update logic
    in a clean, testable way.
    """

    # Map source names to their respective models
    VENDOR_MODEL_MAP = {
        VENDOR_GEMILANG: GemilangProduct,
        VENDOR_DEPO_BANGUNAN: DepoBangunanProduct,
        VENDOR_JURAGAN_MATERIAL: JuraganMaterialProduct,
        VENDOR_MITRA10: Mitra10Product,
        VENDOR_TOKOPEDIA: TokopediaProduct,
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


class UnitUpdateService:
    """Service responsible for updating product units across vendor models.
    
    This service follows the Single Responsibility Principle by focusing solely on
    unit update operations. It handles validation, model lookup, and update logic
    in a clean, testable way.
    """

    # Map source names to their respective models
    VENDOR_MODEL_MAP = {
        VENDOR_GEMILANG: GemilangProduct,
        VENDOR_DEPO_BANGUNAN: DepoBangunanProduct,
        VENDOR_JURAGAN_MATERIAL: JuraganMaterialProduct,
        VENDOR_MITRA10: Mitra10Product,
        VENDOR_TOKOPEDIA: TokopediaProduct,
    }

    def __init__(self, validator: Optional[UnitUpdateRequestValidator] = None):
        """Initialize the unit update service.
        
        Args:
            validator: Optional custom validator instance (for testing/customization)
        """
        self.validator = validator or UnitUpdateRequestValidator()

    def update_unit(self, source: str, product_url: str, new_unit: str) -> Dict:
        """Update the unit of a specific product.
        
        Args:
            source: The vendor source name (e.g., "Gemilang Store")
            product_url: The URL of the product to update
            new_unit: The new unit value to set
            
        Returns:
            Dict containing success status and message, or error information
            
        Raises:
            ValueError: If source is invalid or product not found
        """
        # Validate inputs using the validator
        validation_result = self.validator.validate_update_request(
            source, product_url, new_unit
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
        
        # Store old unit for logging/auditing
        old_unit = product.unit
        
        # Update the unit
        product.unit = new_unit.strip()
        product.save(update_fields=['unit', 'updated_at'])
        
        return {
            "success": True,
            "message": "Unit updated successfully",
            "product_name": product.name,
            "old_unit": old_unit,
            "new_unit": product.unit,
            "vendor": source,
            "updated_at": product.updated_at.isoformat()
        }
    
    def bulk_update_units(self, updates: List[Dict]) -> Dict:
        """Update multiple product units in a single operation.
        
        Args:
            updates: List of dicts with keys: source, product_url, new_unit
            
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
            new_unit = update_data.get("new_unit")
            
            result = self.update_unit(source, product_url, new_unit)
            
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
