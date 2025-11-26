"""
Validators for unit update operations.

This module provides validation logic for unit updates, following the
Single Responsibility Principle. Each validator class handles a specific
type of validation, making the system easily extensible.
"""

from typing import Dict, Optional, List, Any
import re

# Constants
ERROR_UNIT_NONE = "Unit cannot be None"


class UnitValidator:
    """Base validator interface for unit updates.
    
    This abstract base class defines the interface for all unit validators,
    following the Open/Closed Principle - open for extension, closed for modification.
    """
    
    def validate(self, unit: Optional[str]) -> Dict:
        """Validate a unit value.
        
        Args:
            unit: The unit string to validate (can be None for validation testing)
            
        Returns:
            Dict with 'valid' (bool) and optional 'error' (str)
        """
        raise NotImplementedError("Subclasses must implement validate()")


class UnitLengthValidator(UnitValidator):
    """Validates unit string length constraints."""
    
    def __init__(self, min_length: int = 0, max_length: int = 50):
        """Initialize with length constraints.
        
        Args:
            min_length: Minimum allowed length (default: 0)
            max_length: Maximum allowed length (default: 50, matches model)
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, unit: Optional[str]) -> Dict:
        """Validate unit length."""
        if unit is None:
            return {"valid": False, "error": ERROR_UNIT_NONE}
        
        length = len(unit.strip())
        
        if length < self.min_length:
            return {
                "valid": False,
                "error": f"Unit must be at least {self.min_length} characters"
            }
        
        if length > self.max_length:
            return {
                "valid": False,
                "error": f"Unit must not exceed {self.max_length} characters"
            }
        
        return {"valid": True}


class UnitFormatValidator(UnitValidator):
    """Validates unit string format and allowed characters."""
    
    def __init__(self, allow_special_chars: bool = True):
        """Initialize format validator.
        
        Args:
            allow_special_chars: Whether to allow special characters
        """
        self.allow_special_chars = allow_special_chars
        # Pattern allows letters, numbers, spaces, and common punctuation
        self.pattern = re.compile(r'^[\w\s\-.,/()&²³]+$', re.UNICODE)
    
    def validate(self, unit: Optional[str]) -> Dict:
        """Validate unit format."""
        if unit is None:
            return {"valid": False, "error": ERROR_UNIT_NONE}
        
        unit = unit.strip()
        
        if not unit:
            # Empty units are allowed (will default to empty string)
            return {"valid": True}
        
        if not self.allow_special_chars and not self.pattern.match(unit):
            return {
                "valid": False,
                "error": "Unit contains invalid characters"
            }
        
        return {"valid": True}


class UnitBlacklistValidator(UnitValidator):
    """Validates unit against a blacklist of prohibited values."""
    
    def __init__(self, blacklist: Optional[List[str]] = None):
        """Initialize with blacklist.
        
        Args:
            blacklist: List of prohibited unit values (case-insensitive)
        """
        self.blacklist = [item.lower() for item in (blacklist or [])]
    
    def validate(self, unit: Optional[str]) -> Dict:
        """Validate unit against blacklist."""
        if unit is None:
            return {"valid": False, "error": ERROR_UNIT_NONE}
        
        if unit.strip().lower() in self.blacklist:
            return {
                "valid": False,
                "error": "This unit value is not allowed"
            }
        
        return {"valid": True}


class CompositeValidator(UnitValidator):
    """Composite validator that runs multiple validators in sequence.
    
    This follows the Composite Pattern, allowing multiple validators to be
    combined into a single validation pipeline.
    """
    
    def __init__(self, validators: List[UnitValidator]):
        """Initialize with list of validators.
        
        Args:
            validators: List of validator instances to run
        """
        self.validators = validators
    
    def validate(self, unit: Optional[str]) -> Dict:
        """Run all validators in sequence."""
        for validator in self.validators:
            result = validator.validate(unit)
            if not result.get("valid"):
                return result
        
        return {"valid": True}
    
    def add_validator(self, validator: UnitValidator):
        """Add a new validator to the pipeline.
        
        Args:
            validator: Validator instance to add
        """
        self.validators.append(validator)


class UnitUpdateRequestValidator:
    """Validates complete unit update requests.
    
    This class validates the entire request payload for unit updates,
    checking all required fields and their values.
    """
    
    def __init__(self, unit_validator: Optional[UnitValidator] = None):
        """Initialize with optional unit validator.
        
        Args:
            unit_validator: Validator for unit values (default: composite)
        """
        if unit_validator is None:
            # Default composite validator with common rules
            self.unit_validator = CompositeValidator([
                UnitLengthValidator(min_length=0, max_length=50),
                UnitFormatValidator(allow_special_chars=True),
            ])
        else:
            self.unit_validator = unit_validator
    
    def validate_update_request(self, source: Any, product_url: Any, 
                               new_unit: Any) -> Dict:
        """Validate a complete unit update request.
        
        Args:
            source: Vendor source name (validated for type)
            product_url: Product URL (validated for type)
            new_unit: New unit value (validated for type)
            
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
        
        # Validate URL format - only accept HTTPS for security
        if not product_url.startswith("https://"):
            return {"valid": False, "error": "Product URL must be a valid HTTPS URL"}
        
        # Validate new_unit using the unit validator
        if new_unit is None:
            return {"valid": False, "error": "Unit cannot be None"}
        
        if not isinstance(new_unit, str):
            return {"valid": False, "error": "Unit must be a string"}
        
        unit_result = self.unit_validator.validate(new_unit)
        if not unit_result.get("valid"):
            return unit_result
        
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
            new_unit = update.get("new_unit")
            
            result = self.validate_update_request(source, product_url, new_unit)
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
