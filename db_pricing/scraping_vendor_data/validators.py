from django.core.exceptions import ValidationError


class ScrapingVendorDataValidationError(ValidationError):
    """Custom validation error for scraping vendor data."""
    pass


def validate_required_fields(**fields):
    """Validate that all required fields are provided and not empty."""
    for field_name, field_value in fields.items():
        if not field_value or not str(field_value).strip():
            raise ScrapingVendorDataValidationError(f"{field_name.replace('_', ' ').title()} is required")


def validate_field_lengths(**fields):
    """Validate that fields don't exceed maximum length."""
    max_length = 255
    
    for field_name, field_value in fields.items():
        if field_value and len(str(field_value)) > max_length:
            raise ScrapingVendorDataValidationError(
                f"{field_name.replace('_', ' ').title()} cannot exceed {max_length} characters"
            )


def validate_vendor_data(product_name: str, price: str, unit: str, vendor: str, location: str):
    """Main validation function for scraping vendor data."""
    validate_required_fields(
        product_name=product_name,
        price=price,
        unit=unit,
        vendor=vendor,
        location=location
    )
    
    validate_field_lengths(
        product_name=product_name,
        price=price,
        unit=unit,
        vendor=vendor,
        location=location
    )