"""
Validators for category update operations.

This module provides validation logic for category updates, following the
Single Responsibility Principle. Each validator class handles a specific
type of validation, making the system easily extensible.
"""

from typing import Dict, Optional, List, Any
import re

# Constants
ERROR_CATEGORY_NONE = "Category cannot be None"


class CategoryValidator:
    """Base validator interface for category updates.
    
    This abstract base class defines the interface for all category validators,
    following the Open/Closed Principle - open for extension, closed for modification.
    """
    
    def validate(self, category: Optional[str]) -> Dict:
        """Validate a category value.
        
        Args:
            category: The category string to validate (can be None for validation testing)
            
        Returns:
            Dict with 'valid' (bool) and optional 'error' (str)
        """
        raise NotImplementedError("Subclasses must implement validate()")


class CategoryLengthValidator(CategoryValidator):
    """Validates category string length constraints."""
    
    def __init__(self, min_length: int = 0, max_length: int = 100):
        """Initialize with length constraints.
        
        Args:
            min_length: Minimum allowed length (default: 0)
            max_length: Maximum allowed length (default: 100, matches model)
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, category: Optional[str]) -> Dict:
        """Validate category length."""
        if category is None:
            return {"valid": False, "error": ERROR_CATEGORY_NONE}
        
        length = len(category.strip())
        
        if length < self.min_length:
            return {
                "valid": False,
                "error": f"Category must be at least {self.min_length} characters"
            }
        
        if length > self.max_length:
            return {
                "valid": False,
                "error": f"Category must not exceed {self.max_length} characters"
            }
        
        return {"valid": True}


class CategoryFormatValidator(CategoryValidator):
    """Validates category string format and allowed characters."""
    
    def __init__(self, allow_special_chars: bool = True):
        """Initialize format validator.
        
        Args:
            allow_special_chars: Whether to allow special characters
        """
        self.allow_special_chars = allow_special_chars
        # Pattern allows letters, numbers, spaces, and common punctuation
        self.pattern = re.compile(r'^[\w\s\-.,/()&]+$', re.UNICODE)
    
    def validate(self, category: Optional[str]) -> Dict:
        """Validate category format."""
        if category is None:
            return {"valid": False, "error": ERROR_CATEGORY_NONE}
        
        category = category.strip()
        
        if not category:
            # Empty categories are allowed (will default to "Lainnya")
            return {"valid": True}
        
        if not self.allow_special_chars and not self.pattern.match(category):
            return {
                "valid": False,
                "error": "Category contains invalid characters"
            }
        
        return {"valid": True}


class CategoryBlacklistValidator(CategoryValidator):
    """Validates category against a blacklist of prohibited values."""
    
    def __init__(self, blacklist: Optional[List[str]] = None):
        """Initialize with blacklist.
        
        Args:
            blacklist: List of prohibited category values (case-insensitive)
        """
        self.blacklist = [item.lower() for item in (blacklist or [])]
    
    def validate(self, category: Optional[str]) -> Dict:
        """Validate category against blacklist."""
        if category is None:
            return {"valid": False, "error": ERROR_CATEGORY_NONE}
        
        if category.strip().lower() in self.blacklist:
            return {
                "valid": False,
                "error": "This category value is not allowed"
            }
        
        return {"valid": True}


class CompositeValidator(CategoryValidator):
    """Composite validator that runs multiple validators in sequence.
    
    This follows the Composite Pattern, allowing multiple validators to be
    combined into a single validation pipeline.
    """
    
    def __init__(self, validators: List[CategoryValidator]):
        """Initialize with list of validators.
        
        Args:
            validators: List of validator instances to run
        """
        self.validators = validators
    
    def validate(self, category: Optional[str]) -> Dict:
        """Run all validators in sequence."""
        for validator in self.validators:
            result = validator.validate(category)
            if not result.get("valid"):
                return result
        
        return {"valid": True}
    
    def add_validator(self, validator: CategoryValidator):
        """Add a new validator to the pipeline.
        
        Args:
            validator: Validator instance to add
        """
        self.validators.append(validator)


class CategoryUpdateRequestValidator:
    """Validates complete category update requests.
    
    This class validates the entire request payload for category updates,
    checking all required fields and their values.
    """
    
    def __init__(self, category_validator: Optional[CategoryValidator] = None):
        """Initialize with optional category validator.
        
        Args:
            category_validator: Validator for category values (default: composite)
        """
        if category_validator is None:
            # Default composite validator with common rules
            self.category_validator = CompositeValidator([
                CategoryLengthValidator(min_length=0, max_length=100),
                CategoryFormatValidator(allow_special_chars=True),
            ])
        else:
            self.category_validator = category_validator
    
    def validate_update_request(self, source: Any, product_url: Any, 
                               new_category: Any) -> Dict:
        """Validate a complete category update request.
        
        Args:
            source: Vendor source name (validated for type)
            product_url: Product URL (validated for type)
            new_category: New category value (validated for type)
            
        Returns:
            Dict with 'valid' (bool) and optional 'error' (str)
        """
        # Validate source
        if not source or not isinstance(source, str):
            return {"valid": False, "error": "Invalid or missing source"}
        
        if not source.strip():
            return {"valid": False, "error": "Source cannot be empty"}
        
        # Validate product_url
        if not product_url or not isinstance(product_url, str):
            return {"valid": False, "error": "Invalid or missing product_url"}
        
        if not product_url.strip():
            return {"valid": False, "error": "Product URL cannot be empty"}
        
        # Validate URL format (basic check)
        if not (product_url.startswith("http://") or product_url.startswith("https://")):
            return {"valid": False, "error": "Product URL must be a valid HTTP/HTTPS URL"}
        
        # Validate new_category using the category validator
        if new_category is None:
            return {"valid": False, "error": "Category cannot be None"}
        
        if not isinstance(new_category, str):
            return {"valid": False, "error": "Category must be a string"}
        
        category_result = self.category_validator.validate(new_category)
        if not category_result.get("valid"):
            return category_result
        
        return {"valid": True}
    
    def validate_bulk_request(self, updates: Any) -> Dict:
        """Validate a bulk update request.
        
        Args:
            updates: List of update dictionaries (validated for type)
            
        Returns:
            Dict with 'valid' (bool), optional 'error' (str), and 'errors' (list)
        """
        if not isinstance(updates, list):
            return {"valid": False, "error": "Updates must be a list"}
        
        if not updates:
            return {"valid": False, "error": "Updates list cannot be empty"}
        
        if len(updates) > 100:
            return {
                "valid": False, 
                "error": "Bulk updates limited to 100 items at a time"
            }
        
        errors = []
        for i, update in enumerate(updates):
            if not isinstance(update, dict):
                errors.append({
                    "index": i,
                    "error": "Each update must be a dictionary"
                })
                continue
            
            source = update.get("source")
            product_url = update.get("product_url")
            new_category = update.get("new_category")
            
            result = self.validate_update_request(source, product_url, new_category)
            if not result.get("valid"):
                errors.append({
                    "index": i,
                    "error": result.get("error")
                })
        
        if errors:
            return {
                "valid": False,
                "error": f"Validation failed for {len(errors)} items",
                "errors": errors
            }
        
        return {"valid": True}
