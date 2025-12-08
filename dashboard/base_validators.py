"""
Base validators for update operations.

This module provides shared validation logic for both category and unit updates,
eliminating code duplication and following the DRY (Don't Repeat Yourself) principle.
"""

from typing import Dict, Any


class BaseUpdateRequestValidator:
    """Base class for validating update requests.
    
    This class contains common validation logic shared between category and unit
    update validators, reducing code duplication.
    """
    
    @staticmethod
    def validate_source(source: Any) -> Dict:
        """Validate the source field.
        
        Args:
            source: Vendor source name (validated for type)
            
        Returns:
            Dict with 'valid' (bool) and optional 'error' (str)
        """
        if not source or not isinstance(source, str):
            return {"valid": False, "error": "Invalid or missing source"}
        
        if not source.strip():
            return {"valid": False, "error": "Source cannot be empty"}
        
        return {"valid": True}
    
    @staticmethod
    def validate_product_url(product_url: Any) -> Dict:
        """Validate the product_url field.
        
        Args:
            product_url: Product URL (validated for type)
            
        Returns:
            Dict with 'valid' (bool) and optional 'error' (str)
        """
        if not product_url or not isinstance(product_url, str):
            return {"valid": False, "error": "Invalid or missing product_url"}
        
        if not product_url.strip():
            return {"valid": False, "error": "Product URL cannot be empty"}
        
        return {"valid": True}
    
    @staticmethod
    def validate_bulk_request_structure(updates: Any) -> Dict:
        """Validate the structure of a bulk request.
        
        Args:
            updates: List of update dictionaries (validated for type)
            
        Returns:
            Dict with 'valid' (bool) and optional 'error' (str)
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
        
        return {"valid": True}
    
    @staticmethod
    def validate_update_item_structure(update: Any, index: int) -> Dict:
        """Validate the structure of a single update item in a bulk request.
        
        Args:
            update: Single update dictionary
            index: Index of the update in the list
            
        Returns:
            Dict with 'valid' (bool), optional 'error' (str), and 'index' (int)
        """
        if not isinstance(update, dict):
            return {
                "valid": False,
                "index": index,
                "error": "Each update must be a dictionary"
            }
        
        return {"valid": True}
