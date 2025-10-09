from __future__ import annotations

from typing import Protocol, runtime_checkable, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ScrapingVendorData


@runtime_checkable
class ScrapingVendorDataRepository(Protocol):
    """Abstract repository for scraping vendor data operations."""
    
    def create(
        self, 
        *, 
        product_name: str, 
        price: str, 
        unit: str, 
        vendor: str, 
        location: str
    ) -> "ScrapingVendorData": ...
    
    def get_by_id(self, vendor_data_id: int) -> Optional["ScrapingVendorData"]: ...
    
    def get_all(self) -> List["ScrapingVendorData"]: ...
    
    def filter_by_vendor(self, vendor: str) -> List["ScrapingVendorData"]: ...
    
    def filter_by_location(self, location: str) -> List["ScrapingVendorData"]: ...
    
    def update(
        self, 
        vendor_data_id: int, 
        *, 
        product_name: str = None, 
        price: str = None, 
        unit: str = None, 
        vendor: str = None, 
        location: str = None
    ) -> Optional["ScrapingVendorData"]: ...
    
    def delete(self, vendor_data_id: int) -> bool: ...
    
    def table_exists(self) -> bool: ...


@runtime_checkable
class ScrapingVendorDataValidator(Protocol):
    """Interface for business validation rules for scraping vendor data."""
    
    code: str  # machine readable id
    
    def validate(self, ctx: "ScrapingVendorDataContext") -> None: ...  # raise ValidationError on failure


class ScrapingVendorDataContext:
    """Immutable data passed to validators."""
    
    __slots__ = ("product_name", "price", "unit", "vendor", "location")
    
    def __init__(
        self, 
        *, 
        product_name: str, 
        price: str, 
        unit: str, 
        vendor: str, 
        location: str
    ):
        self.product_name = product_name
        self.price = price
        self.unit = unit
        self.vendor = vendor
        self.location = location
    
    def with_updates(self, **changes) -> "ScrapingVendorDataContext":
        """Create a new context with updated values."""
        data = {
            "product_name": self.product_name,
            "price": self.price,
            "unit": self.unit,
            "vendor": self.vendor,
            "location": self.location,
        }
        data.update(changes)
        return ScrapingVendorDataContext(**data)