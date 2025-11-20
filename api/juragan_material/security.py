"""
OWASP Security Module for Juragan Material API
Implements A01:2021 (Broken Access Control), A03:2021 (Injection), A04:2021 (Insecure Design)

This module extends the shared security components from api.gemilang.security
with Juragan Material-specific configurations.
"""
import logging
import re
from typing import Any, Optional, Tuple

# Import shared security components from Gemilang
from api.gemilang.security import (
    RateLimiter,
    InputValidator as BaseInputValidator,
    DatabaseQueryValidator as BaseDatabaseQueryValidator,
    SecurityDesignPatterns as BaseSecurityDesignPatterns,
    AccessControlManager as BaseAccessControlManager,
    rate_limiter,
    require_api_token,
    validate_input,
    enforce_resource_limits,
)
from django.core.cache import cache
from datetime import datetime

logger = logging.getLogger('api.juragan_material.security')


# =============================================================================
# Juragan Material Specific Configurations
# =============================================================================

class InputValidator(BaseInputValidator):
    """
    Extended InputValidator with additional methods for Juragan Material.
    """
    
    @classmethod
    def validate_integer_param(
        cls, 
        value: Any, 
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate integer parameter (alias for validate_integer with different return order).
        Returns: (is_valid, value, error_message)
        """
        is_valid, error_msg, validated_value = cls.validate_integer(value, field_name, min_value, max_value)
        # Convert empty string to None for consistency with test expectations
        error_msg = error_msg if error_msg else None
        return is_valid, validated_value, error_msg
    
    @classmethod
    def validate_boolean_param(cls, value: Any, field_name: str) -> Tuple[bool, Optional[bool], Optional[str]]:
        """
        Validate boolean parameter (alias for validate_boolean with different return order).
        Returns: (is_valid, value, error_message)
        """
        is_valid, error_msg, validated_value = cls.validate_boolean(value, field_name)
        return is_valid, validated_value, error_msg
    
    @classmethod
    def validate_sort_type(cls, value: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate sort_type parameter against whitelist.
        Returns: (is_valid, value, error_message)
        """
        if not value:
            return False, None, "sort_type cannot be empty"
        
        allowed_values = ['cheapest', 'popularity', 'relevance']
        value_lower = value.lower()
        
        if value_lower not in allowed_values:
            return False, None, f"sort_type must be one of: {', '.join(allowed_values)}"
        
        return True, value_lower, None
    
    @classmethod
    def sanitize_for_logging(cls, value: str) -> str:
        """
        Sanitize input for logging to prevent log injection.
        Removes newlines and carriage returns.
        """
        if not value:
            return ""
        
        # Remove newlines and carriage returns
        sanitized = value.replace('\n', '').replace('\r', '')
        
        # Remove non-printable characters
        sanitized = ''.join(c if c.isprintable() or c == ' ' else '' for c in sanitized)
        
        # Limit length
        return sanitized[:500]


class AccessControlManager(BaseAccessControlManager):
    """
    Extended AccessControlManager for Juragan Material with module-specific logging.
    """
    
    @classmethod
    def log_access_attempt(cls, request, success: bool, reason: str = ''):
        """
        Log access control events for monitoring and alerting.
        Uses Juragan Material specific logger.
        """
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        # Sanitize all user-controlled data to prevent log injection
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:200]
        user_agent = ''.join(c if c.isprintable() else '' for c in user_agent)
        path = request.path[:200]
        path = ''.join(c if c.isprintable() else '' for c in path)
        method = request.method
        # Sanitize reason field (user-controlled)
        safe_reason = str(reason)[:100] if reason else 'unknown'
        safe_reason = ''.join(c if c.isprintable() else '' for c in safe_reason)
        
        # Log with sanitized values - don't log raw user input
        timestamp = datetime.now().isoformat()
        
        if success:
            logger.info(
                f"Access granted - IP: {client_ip}, Path: {path}, Method: {method}, Time: {timestamp}"
            )
        else:
            logger.warning(
                f"Access denied - IP: {client_ip}, Path: {path}, Method: {method}, "
                f"Reason: {safe_reason}, Time: {timestamp}"
            )
            # In production: Alert admins on repeated failures
            cls._check_for_attack_pattern(client_ip)
    
    @classmethod
    def _check_for_attack_pattern(cls, client_ip: str):
        """
        Monitor for potential attack patterns.
        Alert admins on suspicious activity.
        """
        cache_key = f"failed_access_{client_ip}"
        failures = cache.get(cache_key, 0)
        failures += 1
        cache.set(cache_key, failures, 300)  # 5 minutes
        
        if failures > 10:
            logger.critical(
                f"SECURITY ALERT: Multiple access control failures from {client_ip}. "
                f"Possible attack in progress. Failed attempts: {failures}"
            )
            # In production: Send alert to admins, consider IP blocking


class SecurityDesignPatterns(BaseSecurityDesignPatterns):
    """
    Extended SecurityDesignPatterns for Juragan Material with SSRF protection.
    """
    
    @staticmethod
    def _validate_url_field(url: str) -> Tuple[bool, str]:
        """
        Validate URL field with enhanced SSRF protection for Juragan Material.
        """
        if not url.startswith('https://'):
            return False, "URL must use HTTPS protocol for security"
        
        # SSRF prevention - block internal addresses
        internal_patterns = [
            'localhost', '127.0.0.1', '0.0.0.0',
            '::1',  # IPv6 loopback
            '169.254.',  # Link-local
            '10.',  # Private network
            '172.16.', '172.17.', '172.18.', '172.19.',
            '172.20.', '172.21.', '172.22.', '172.23.',
            '172.24.', '172.25.', '172.26.', '172.27.',
            '172.28.', '172.29.', '172.30.', '172.31.',  # Private network
            '192.168.',  # Private network
            '192.0.2.',  # TEST-NET-1 (documentation)
            '198.51.100.',  # TEST-NET-2 (documentation)
            '203.0.113.',  # TEST-NET-3 (documentation)
        ]
        
        url_lower = url.lower()
        for pattern in internal_patterns:
            if pattern in url_lower:
                logger.critical(f"SSRF attempt detected: {url}")
                return False, "Invalid URL"
        
        return True, ""
    
    @staticmethod
    def validate_business_logic(data: dict) -> Tuple[bool, str]:
        """
        Validate business logic constraints for Juragan Material.
        Overrides parent to use enhanced URL validation.
        """
        if 'price' in data:
            is_valid, error_msg = SecurityDesignPatterns._validate_price_field(data['price'])
            if not is_valid:
                return False, error_msg
        
        if 'name' in data:
            is_valid, error_msg = SecurityDesignPatterns._validate_name_field(data['name'])
            if not is_valid:
                return False, error_msg
        
        if 'url' in data:
            is_valid, error_msg = SecurityDesignPatterns._validate_url_field(data['url'])
            if not is_valid:
                return False, error_msg
        
        return True, ""


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
    'AccessControlManager',
    'rate_limiter',
    'require_api_token',
    'validate_input',
    'enforce_resource_limits',
]

