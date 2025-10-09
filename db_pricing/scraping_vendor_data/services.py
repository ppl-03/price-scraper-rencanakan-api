from typing import List, Optional
from django.core.exceptions import ValidationError
from django.db import connection
from .models import ScrapingVendorData
from .interfaces import ScrapingVendorDataRepository, ScrapingVendorDataValidator, ScrapingVendorDataContext


class DjangoScrapingVendorDataRepository:
    """Django ORM implementation of ScrapingVendorDataRepository."""
    
    def create(
        self, 
        *, 
        product_name: str, 
        price: str, 
        unit: str, 
        vendor: str, 
        location: str
    ) -> ScrapingVendorData:
        """Create a new scraping vendor data record."""
        return ScrapingVendorData.objects.create(
            product_name=product_name,
            price=price,
            unit=unit,
            vendor=vendor,
            location=location
        )
    
    def get_by_id(self, vendor_data_id: int) -> Optional[ScrapingVendorData]:
        """Get scraping vendor data by ID."""
        try:
            return ScrapingVendorData.objects.get(id=vendor_data_id)
        except ScrapingVendorData.DoesNotExist:
            return None
    
    def get_all(self) -> List[ScrapingVendorData]:
        """Get all scraping vendor data records."""
        return list(ScrapingVendorData.objects.all())
    
    def filter_by_vendor(self, vendor: str) -> List[ScrapingVendorData]:
        """Filter records by vendor name."""
        return list(ScrapingVendorData.objects.filter(vendor=vendor))
    
    def filter_by_location(self, location: str) -> List[ScrapingVendorData]:
        """Filter records by location."""
        return list(ScrapingVendorData.objects.filter(location=location))
    
    def update(
        self, 
        vendor_data_id: int, 
        *, 
        product_name: str = None, 
        price: str = None, 
        unit: str = None, 
        vendor: str = None, 
        location: str = None
    ) -> Optional[ScrapingVendorData]:
        """Update scraping vendor data record."""
        try:
            vendor_data = ScrapingVendorData.objects.get(id=vendor_data_id)
            
            if product_name is not None:
                vendor_data.product_name = product_name
            if price is not None:
                vendor_data.price = price
            if unit is not None:
                vendor_data.unit = unit
            if vendor is not None:
                vendor_data.vendor = vendor
            if location is not None:
                vendor_data.location = location
            
            vendor_data.save()
            return vendor_data
        except ScrapingVendorData.DoesNotExist:
            return None
    
    def delete(self, vendor_data_id: int) -> bool:
        """Delete scraping vendor data record."""
        try:
            vendor_data = ScrapingVendorData.objects.get(id=vendor_data_id)
            vendor_data.delete()
            return True
        except ScrapingVendorData.DoesNotExist:
            return False
    
    def table_exists(self) -> bool:
        """Check if the scraping vendor data table exists in the database."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables 
                WHERE table_name = %s
            """, ['scraping_vendor_data'])
            result = cursor.fetchone()
            return result[0] > 0


class ScrapingVendorDataService:
    """Service layer for scraping vendor data operations."""
    
    def __init__(
        self, 
        repository: ScrapingVendorDataRepository,
        validators: List[ScrapingVendorDataValidator] = None
    ):
        self.repository = repository
        self.validators = validators or []
    
    def create_vendor_data(
        self, 
        *, 
        product_name: str, 
        price: str, 
        unit: str, 
        vendor: str, 
        location: str
    ) -> ScrapingVendorData:
        """Create new vendor data with validation."""
        # Create context for validation
        ctx = ScrapingVendorDataContext(
            product_name=product_name,
            price=price,
            unit=unit,
            vendor=vendor,
            location=location
        )
        
        # Run all validators
        for validator in self.validators:
            validator.validate(ctx)
        
        # Create the record
        return self.repository.create(
            product_name=product_name,
            price=price,
            unit=unit,
            vendor=vendor,
            location=location
        )
    
    def get_vendor_data_by_id(self, vendor_data_id: int) -> Optional[ScrapingVendorData]:
        """Get vendor data by ID."""
        return self.repository.get_by_id(vendor_data_id)
    
    def get_all_vendor_data(self) -> List[ScrapingVendorData]:
        """Get all vendor data records."""
        return self.repository.get_all()
    
    def get_vendor_data_by_vendor(self, vendor: str) -> List[ScrapingVendorData]:
        """Get vendor data by vendor name."""
        return self.repository.filter_by_vendor(vendor)
    
    def get_vendor_data_by_location(self, location: str) -> List[ScrapingVendorData]:
        """Get vendor data by location."""
        return self.repository.filter_by_location(location)
    
    def update_vendor_data(
        self, 
        vendor_data_id: int, 
        **updates
    ) -> Optional[ScrapingVendorData]:
        """Update vendor data with validation."""
        # First check if record exists
        existing = self.repository.get_by_id(vendor_data_id)
        if not existing:
            return None
        
        # Create context with current values and updates
        ctx = ScrapingVendorDataContext(
            product_name=updates.get('product_name', existing.product_name),
            price=updates.get('price', existing.price),
            unit=updates.get('unit', existing.unit),
            vendor=updates.get('vendor', existing.vendor),
            location=updates.get('location', existing.location)
        )
        
        # Run all validators
        for validator in self.validators:
            validator.validate(ctx)
        
        # Update the record
        return self.repository.update(vendor_data_id, **updates)
    
    def delete_vendor_data(self, vendor_data_id: int) -> bool:
        """Delete vendor data."""
        return self.repository.delete(vendor_data_id)
    
    def ensure_table_exists(self) -> bool:
        """Ensure the table exists, create if it doesn't."""
        if not self.repository.table_exists():
            # Import here to avoid circular imports
            from django.core.management import execute_from_command_line
            import sys
            
            # Run migrations to create the table
            try:
                execute_from_command_line(['manage.py', 'makemigrations', 'scraping_vendor_data'])
                execute_from_command_line(['manage.py', 'migrate'])
                return True
            except Exception:
                return False
        return True


# Basic validators
class RequiredFieldsValidator:
    """Validator to ensure all required fields are provided."""
    
    code = "required_fields"
    
    def validate(self, ctx: ScrapingVendorDataContext) -> None:
        """Validate that all required fields are present and not empty."""
        if not ctx.product_name or not ctx.product_name.strip():
            raise ValidationError("Product name is required")
        
        if not ctx.price or not ctx.price.strip():
            raise ValidationError("Price is required")
        
        if not ctx.unit or not ctx.unit.strip():
            raise ValidationError("Unit is required")
        
        if not ctx.vendor or not ctx.vendor.strip():
            raise ValidationError("Vendor is required")
        
        if not ctx.location or not ctx.location.strip():
            raise ValidationError("Location is required")


class FieldLengthValidator:
    """Validator to ensure fields don't exceed maximum length."""
    
    code = "field_length"
    
    def validate(self, ctx: ScrapingVendorDataContext) -> None:
        """Validate field lengths."""
        max_length = 255
        
        if len(ctx.product_name) > max_length:
            raise ValidationError(f"Product name cannot exceed {max_length} characters")
        
        if len(ctx.price) > max_length:
            raise ValidationError(f"Price cannot exceed {max_length} characters")
        
        if len(ctx.unit) > max_length:
            raise ValidationError(f"Unit cannot exceed {max_length} characters")
        
        if len(ctx.vendor) > max_length:
            raise ValidationError(f"Vendor cannot exceed {max_length} characters")
        
        if len(ctx.location) > max_length:
            raise ValidationError(f"Location cannot exceed {max_length} characters")