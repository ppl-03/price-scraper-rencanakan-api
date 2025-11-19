"""
OWASP Security Module for Juragan Material API
Implements A01:2021 (Broken Access Control), A03:2021 (Injection), A04:2021 (Insecure Design)

This module extends the shared security components from api.gemilang.security
with Juragan Material-specific configurations.
"""
import logging

# Import shared security components from Gemilang
from api.gemilang.security import (
    RateLimiter,
    InputValidator,
    DatabaseQueryValidator as BaseDatabaseQueryValidator,
    SecurityDesignPatterns,
    OrmSecurityHelper,
    rate_limiter,
    require_api_token,
    validate_input,
    enforce_resource_limits,
    AccessControlManager,
)

logger = logging.getLogger('api.juragan_material.security')


# =============================================================================
# Juragan Material Specific Configurations
# =============================================================================

class DatabaseQueryValidator(BaseDatabaseQueryValidator):
    """
    Juragan Material specific database query validator.
    Overrides table and column whitelists for Juragan Material database schema.
    """
    
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """
        Validate table name against Juragan Material whitelist.
        """
        allowed_tables = [
            'juragan_material_products',
            'juragan_material_locations',
            'juragan_material_price_history'
        ]
        return table_name in allowed_tables
    
    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        """
        Validate column name against Juragan Material whitelist.
        """
        allowed_columns = [
            'id', 'name', 'price', 'url', 'unit', 'location',
            'created_at', 'updated_at', 'code', 'category'
        ]
        return column_name in allowed_columns


# Export all security components for use in Juragan Material module
__all__ = [
    'RateLimiter',
    'InputValidator',
    'DatabaseQueryValidator',
    'SecurityDesignPatterns',
    'OrmSecurityHelper',
    'AccessControlManager',
    'rate_limiter',
    'require_api_token',
    'validate_input',
    'enforce_resource_limits',
]
