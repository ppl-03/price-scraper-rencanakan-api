"""
OWASP Security Module for Depobangunan API
Implements A01:2021 (Broken Access Control), A03:2021 (Injection), A04:2021 (Insecure Design)

Architecture:
- Class-based validation with method chaining  
- Token-based access control with role management
- Sliding window rate limiting with deque-based tracking
- Validation pipeline with early termination
"""
import logging
import re
import time
import json
from functools import wraps
from typing import Optional, Dict, Any, Tuple, List, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection
import bleach

logger = logging.getLogger(__name__)


# =============================================================================
# A01:2021 – Broken Access Control Prevention
# =============================================================================

class RateLimitTracker:
    """
    Sliding window rate limiter with deque-based request tracking.
    Uses efficient data structures for high-performance rate limiting.
    """
    def __init__(self):
        self.request_history = defaultdict(deque)
        self.blocked_until = {}
        
    def record_request(self, identifier: str, window_size: int) -> int:
        """Record a request and return current count in window."""
        now = time.time()
        cutoff = now - window_size
        
        # Remove old requests efficiently with deque
        history = self.request_history[identifier]
        while history and history[0] < cutoff:
            history.popleft()
        
        history.append(now)
        return len(history)
    
    def check_if_blocked(self, identifier: str) -> Tuple[bool, int]:
        """Check if identifier is currently blocked."""
        if identifier not in self.blocked_until:
            return False, 0
        
        now = time.time()
        unblock_time = self.blocked_until[identifier]
        
        if now >= unblock_time:
            del self.blocked_until[identifier]
            return False, 0
        
        return True, int(unblock_time - now)
    
    def apply_block(self, identifier: str, duration: int):
        """Block an identifier for specified duration."""
        self.blocked_until[identifier] = time.time() + duration
        logger.warning(f"Rate limit block applied: {identifier} for {duration}s")


class RateLimiter:
    """
    Rate limiting implementation using sliding window algorithm.
    Implements OWASP A01:2021 - Rate limit API and controller access.
    """
    def __init__(self):
        self.tracker = RateLimitTracker()
        
    def check_rate_limit(
        self, 
        client_id: str, 
        max_requests: int = 100, 
        window_seconds: int = 60,
        block_on_violation: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate request against rate limits using sliding window.
        
        Returns:
            (is_allowed, error_message)
        """
        # Check for existing block
        is_blocked, remaining = self.tracker.check_if_blocked(client_id)
        if is_blocked:
            return False, f"Rate limit exceeded. Blocked for {remaining} more seconds"
        
        # Count requests in window
        request_count = self.tracker.record_request(client_id, window_seconds)
        
        # Enforce limit
        if request_count > max_requests:
            if block_on_violation:
                self.tracker.apply_block(client_id, 300)
            
            logger.warning(
                f"Rate limit violation: {client_id} made {request_count} "
                f"requests (limit: {max_requests}/{window_seconds}s)"
            )
            return False, f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds"
        
        return True, None
    
    def is_blocked(self, client_id: str) -> bool:
        """Legacy compatibility method."""
        is_blocked, _ = self.tracker.check_if_blocked(client_id)
        return is_blocked
    
    def block_client(self, client_id: str, duration_seconds: int = 300):
        """Legacy compatibility method."""
        self.tracker.apply_block(client_id, duration_seconds)


# Global rate limiter instance
rate_limiter = RateLimiter()


class TokenRegistry:
    """Centralized token storage and retrieval."""
    
    TOKENS = {
        'dev-token-12345': {
            'name': 'Development Token',
            'owner': 'dev-team',
            'permissions': ['read', 'write', 'scrape'],
            'allowed_ips': [],
            'rate_limit': {'requests': 100, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        },
        'legacy-api-token-67890': {
            'name': 'Legacy Client Token',
            'owner': 'legacy-client',
            'permissions': ['read', 'scrape'],
            'allowed_ips': [],
            'rate_limit': {'requests': 50, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        },
        'read-only-token': {
            'name': 'Read Only Token',
            'owner': 'monitoring',
            'permissions': ['read'],
            'allowed_ips': [],
            'rate_limit': {'requests': 200, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        }
    }
    
    @classmethod
    def get(cls, token: str) -> Optional[Dict]:
        """Retrieve token information."""
        return cls.TOKENS.get(token)
    
    @classmethod
    def exists(cls, token: str) -> bool:
        """Check if token exists."""
        return token in cls.TOKENS


class AccessValidator:
    """
    Multi-stage access validation pipeline.
    Each validation method can terminate the chain early on failure.
    """
    
    @staticmethod
    def extract_token_from_request(request) -> Optional[str]:
        """Extract API token from request headers."""
        # Try X-API-Token header first
        token = request.headers.get('X-API-Token')
        if token:
            return token
        
        # Check Authorization header - support both Bearer and raw token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header:
            auth_header = request.headers.get('Authorization', '')
        
        if auth_header:
            if auth_header.startswith('Bearer '):
                return auth_header[7:]  # Remove 'Bearer ' prefix
            else:
                # Support raw token in Authorization header (for test compatibility)
                return auth_header
        
        return None
    
    @staticmethod
    def verify_token_exists(token: Optional[str], client_ip: str) -> Tuple[bool, str, Optional[Dict]]:
        """Verify that token exists and is valid."""
        if not token:
            return False, 'API token required', None
        
        token_data = TokenRegistry.get(token)
        if not token_data:
            logger.warning(f"Unknown token attempted from {client_ip}")
            return False, 'Invalid API token', None
        
        return True, '', token_data
    
    @staticmethod
    def verify_ip_authorization(token_data: Dict, client_ip: str) -> Tuple[bool, str]:
        """Verify client IP is authorized for token."""
        allowed_ips = token_data.get('allowed_ips', [])
        
        # Empty list means all IPs allowed
        if not allowed_ips:
            return True, ''
        
        if client_ip not in allowed_ips:
            logger.warning(
                f"Unauthorized IP {client_ip} for token '{token_data['name']}'"
            )
            return False, 'IP not authorized for this token'
        
        return True, ''
    
    @staticmethod
    def verify_permission(token_data: Dict, required_perm: str) -> bool:
        """Check if token has required permission."""
        perms = token_data.get('permissions', [])
        has_perm = required_perm in perms
        
        if not has_perm:
            logger.warning(
                f"Permission '{required_perm}' denied for token '{token_data['name']}'"
            )
        
        return has_perm


class SecurityAuditLog:
    """Centralized security event logging and monitoring."""
    
    @staticmethod
    def sanitize_for_log(value: str, max_len: int = 200) -> str:
        """Sanitize user input for safe logging."""
        if not value:
            return 'unknown'
        
        truncated = str(value)[:max_len]
        return ''.join(c if c.isprintable() else '' for c in truncated)
    
    @staticmethod
    def log_access_event(request, granted: bool, reason: str = ''):
        """Log access control events with sanitized data."""
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        path = SecurityAuditLog.sanitize_for_log(request.path)
        method = request.method
        safe_reason = SecurityAuditLog.sanitize_for_log(reason, 100)
        timestamp = datetime.now().isoformat()
        
        if granted:
            logger.info(
                f"Access granted - IP: {ip}, Path: {path}, Method: {method}, Time: {timestamp}"
            )
        else:
            logger.warning(
                f"Access denied - IP: {ip}, Path: {path}, Method: {method}, "
                f"Reason: {safe_reason}, Time: {timestamp}"
            )
            SecurityAuditLog.check_attack_indicators(ip)
    
    @staticmethod
    def check_attack_indicators(client_ip: str):
        """Monitor for attack patterns and alert on suspicious activity."""
        cache_key = f"failed_access_{client_ip}"
        failures = cache.get(cache_key, 0) + 1
        cache.set(cache_key, failures, 300)
        
        if failures > 10:
            logger.critical(
                f"SECURITY ALERT: Multiple access control failures from {client_ip}. "
                f"Possible attack in progress. Failed attempts: {failures}"
            )


class AccessControlManager:
    """
    Orchestrates access control validation pipeline.
    Implements OWASP A01:2021 - Broken Access Control prevention.
    """
    
    # Create a direct reference to TokenRegistry.TOKENS so patches to either work
    # This allows: patch.object(AccessControlManager, 'API_TOKENS', {...})
    API_TOKENS = TokenRegistry.TOKENS
    
    @classmethod
    def validate_token(cls, request) -> Tuple[bool, str, Optional[Dict]]:
        """
        Execute token validation pipeline.
        Returns: (is_valid, error_message, token_info)
        """
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Stage 1: Extract token
        token = AccessValidator.extract_token_from_request(request)
        
        # Stage 2: Verify token exists - check cls.API_TOKENS to support patching
        if not token:
            return False, 'API token required', None
        
        token_data = cls.API_TOKENS.get(token)
        if not token_data:
            logger.warning(f"Unknown token attempted from {client_ip}")
            return False, 'Invalid API token', None
        
        # Stage 3: Verify IP authorization
        is_authorized, error = AccessValidator.verify_ip_authorization(token_data, client_ip)
        if not is_authorized:
            return False, error, None
        
        # Log successful validation
        logger.info(f"Valid API token used from {client_ip}: {token_data['name']}")
        return True, '', token_data
    
    @classmethod
    def check_permission(cls, token_info: Dict, required_permission: str) -> bool:
        """Verify token has required permission."""
        return AccessValidator.verify_permission(token_info, required_permission)
    
    @classmethod
    def log_access_attempt(cls, request, success: bool, reason: str = ''):
        """Log access attempts for audit trail."""
        SecurityAuditLog.log_access_event(request, success, reason)
    
    @classmethod
    def _check_for_attack_pattern(cls, client_ip: str):
        """Legacy compatibility for attack pattern detection."""
        SecurityAuditLog.check_attack_indicators(client_ip)


# =============================================================================
# A03:2021 – Injection Prevention
# =============================================================================

class ValidationRule:
    """Base class for validation rules using chain of responsibility pattern."""
    
    def __init__(self, field_name: str):
        self.field_name = field_name
        self.next_rule = None
    
    def set_next(self, rule: 'ValidationRule') -> 'ValidationRule':
        """Chain the next validation rule."""
        self.next_rule = rule
        return rule
    
    def validate(self, value: Any) -> Tuple[bool, str, Any]:
        """Execute validation and pass to next rule if successful."""
        is_valid, error, processed_value = self._validate_impl(value)
        
        if not is_valid:
            return False, error, None
        
        if self.next_rule:
            return self.next_rule.validate(processed_value)
        
        return True, "", processed_value
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        """Override in subclasses to implement specific validation."""
        return True, "", value


class RequiredRule(ValidationRule):
    """Validates that value is not None or empty."""
    
    def __init__(self, field_name: str, error_msg: str = None):
        super().__init__(field_name)
        self.error_msg = error_msg or f"{field_name} is required"
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if value is None or value == '':
            return False, self.error_msg, None
        return True, "", value


class LengthRule(ValidationRule):
    """Validates string length."""
    
    def __init__(self, field_name: str, min_len: int = None, max_len: int = None):
        super().__init__(field_name)
        self.min_len = min_len
        self.max_len = max_len
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if not isinstance(value, str):
            return True, "", value  # Skip if not string
        
        length = len(value)
        
        if self.min_len and length < self.min_len:
            return False, f"{self.field_name} must be at least {self.min_len} characters", None
        
        if self.max_len and length > self.max_len:
            return False, f"{self.field_name} exceeds maximum length of {self.max_len}", None
        
        return True, "", value


class PatternRule(ValidationRule):
    """Validates value against regex pattern."""
    
    def __init__(self, field_name: str, pattern: re.Pattern, error_msg: str):
        super().__init__(field_name)
        self.pattern = pattern
        self.error_msg = error_msg
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if not isinstance(value, str):
            return True, "", value
        
        if not self.pattern.match(value):
            logger.warning(f"Pattern validation failed for {self.field_name}: {value}")
            return False, self.error_msg, None
        
        return True, "", value


class SqlInjectionRule(ValidationRule):
    """Detects SQL injection patterns."""
    
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(;)",  # Semicolon for SQL statement termination
        r"(\-\-)",  # SQL comment
        r"(\/\*|\*\/)",  # Multi-line comment
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(\'|\"|`)",
        r"(<script)",  # XSS detection
        r"(<iframe)",  # XSS iframe
        r"(javascript:)",  # JavaScript protocol
        r"(onerror=)",  # Event handler XSS
    ]
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if not isinstance(value, str):
            return True, "", value
        
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.critical(f"SQL injection detected in {self.field_name}: {value}")
                return False, f"Invalid {self.field_name} format", None
        
        return True, "", value


class SanitizeRule(ValidationRule):
    """Sanitizes HTML and dangerous characters."""
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if not isinstance(value, str):
            return True, "", value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # HTML sanitization
        sanitized = bleach.clean(value, tags=[], strip=True)
        
        return True, "", sanitized


class StripWhitespaceRule(ValidationRule):
    """Strips leading/trailing whitespace."""
    
    def __init__(self, field_name: str, check_empty: bool = False):
        super().__init__(field_name)
        self.check_empty = check_empty
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if isinstance(value, str):
            stripped = value.strip()
            if self.check_empty and not stripped:
                return False, f"{self.field_name} cannot be empty", None
            return True, "", stripped
        return True, "", value


class TypeConversionRule(ValidationRule):
    """Converts value to specified type."""
    
    def __init__(self, field_name: str, target_type: type):
        super().__init__(field_name)
        self.target_type = target_type
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if isinstance(value, self.target_type):
            return True, "", value
        
        try:
            converted = self.target_type(value)
            return True, "", converted
        except (ValueError, TypeError):
            type_name = 'integer' if self.target_type == int else self.target_type.__name__
            return False, f"{self.field_name} must be a valid {type_name}", None


class RangeRule(ValidationRule):
    """Validates numeric range."""
    
    def __init__(self, field_name: str, min_val: Optional[int] = None, max_val: Optional[int] = None):
        super().__init__(field_name)
        self.min_val = min_val
        self.max_val = max_val
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if not isinstance(value, (int, float)):
            return True, "", value
        
        if self.min_val is not None and value < self.min_val:
            return False, f"{self.field_name} must be at least {self.min_val}", None
        
        if self.max_val is not None and value > self.max_val:
            return False, f"{self.field_name} must be at most {self.max_val}", None
        
        return True, "", value


class BooleanConversionRule(ValidationRule):
    """Converts string to boolean with SQL injection protection."""
    
    VALID_TRUE = ['true', '1', 'yes']
    VALID_FALSE = ['false', '0', 'no']
    SQL_PATTERNS = ['select', 'insert', 'update', 'delete', 'drop', 'union',
                    '--', ';', '/*', '*/', 'xp_', 'sp_', 'exec', 'execute', "'", '"']
    
    def _validate_impl(self, value: Any) -> Tuple[bool, str, Any]:
        if value is None:
            return True, "", None
        
        if isinstance(value, bool):
            return True, "", value
        
        if not isinstance(value, str):
            return False, f"{self.field_name} must be a boolean value", None
        
        value_lower = value.strip().lower()
        
        if not value_lower:
            return False, f"{self.field_name} cannot be empty", None
        
        # Check for SQL injection
        if any(pattern in value_lower for pattern in self.SQL_PATTERNS):
            logger.warning(f"SQL injection attempt in boolean field '{self.field_name}'")
            return False, f"{self.field_name} contains forbidden characters", None
        
        if value_lower in self.VALID_TRUE:
            return True, "", True
        elif value_lower in self.VALID_FALSE:
            return True, "", False
        else:
            return False, f"{self.field_name} must be 'true', 'false', '1', '0', 'yes', or 'no'", None


class ValidationChainBuilder:
    """Fluent API for building validation chains."""
    
    @staticmethod
    def for_keyword(field_name: str = 'keyword', max_length: int = 100) -> ValidationRule:
        """Build validation chain for keyword input."""
        chain = RequiredRule(field_name, "Keyword is required")
        # Strip whitespace first and check if empty
        chain.set_next(StripWhitespaceRule(field_name, check_empty=True)) \
             .set_next(LengthRule(field_name, max_len=max_length)) \
             .set_next(SqlInjectionRule(field_name)) \
             .set_next(PatternRule(
                 field_name,
                 re.compile(r'^[a-zA-Z0-9\s\-_\.]+$'),
                 "Keyword contains invalid characters. Only alphanumeric, spaces, hyphens, underscores, and periods allowed"
             )) \
             .set_next(SanitizeRule(field_name))
        return chain
    
    @staticmethod
    def for_integer(field_name: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> ValidationRule:
        """Build validation chain for integer input."""
        chain = RequiredRule(field_name, f"{field_name} is required")
        
        # Try to convert string to int
        if min_val is not None or max_val is not None:
            chain.set_next(TypeConversionRule(field_name, int)) \
                 .set_next(RangeRule(field_name, min_val, max_val))
        else:
            chain.set_next(TypeConversionRule(field_name, int))
        
        return chain
    
    @staticmethod
    def for_boolean(field_name: str) -> ValidationRule:
        """Build validation chain for boolean input."""
        return BooleanConversionRule(field_name)


class InputValidator:
    """
    Validation facade using chain of responsibility pattern.
    Implements OWASP A03:2021 - Injection prevention.
    """
    
    @classmethod
    def validate_keyword(cls, keyword: str, max_length: int = 100) -> Tuple[bool, str, Optional[str]]:
        """Validate keyword input using validation chain."""
        chain = ValidationChainBuilder.for_keyword('keyword', max_length)
        return chain.validate(keyword)
    
    @classmethod
    def validate_integer(
        cls,
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """Validate integer input using validation chain."""
        chain = ValidationChainBuilder.for_integer(field_name, min_value, max_value)
        return chain.validate(value)
    
    @classmethod
    def validate_boolean(cls, value: Any, field_name: str) -> Tuple[bool, str, Optional[bool]]:
        """Validate boolean input using validation chain."""
        chain = ValidationChainBuilder.for_boolean(field_name)
        return chain.validate(value)
    
    # Legacy helper methods for backward compatibility
    @classmethod
    def _validate_boolean_string(cls, value: str, field_name: str) -> Tuple[bool, str, Optional[bool]]:
        """Legacy method - redirects to chain-based validation."""
        return cls.validate_boolean(value, field_name)
    
    @classmethod
    def _contains_sql_injection_pattern(cls, value: str) -> bool:
        """Legacy method - check for SQL injection patterns."""
        sql_patterns = BooleanConversionRule.SQL_PATTERNS
        return any(pattern in value for pattern in sql_patterns)
    
    @classmethod
    def _parse_boolean_value(cls, value_stripped: str, field_name: str) -> Tuple[bool, str, Optional[bool]]:
        """Legacy method - redirects to chain-based validation."""
        return cls.validate_boolean(value_stripped, field_name)
    
    @classmethod
    def _detect_sql_injection(cls, value: str) -> bool:
        """Legacy method - detect SQL injection."""
        sql_patterns = SqlInjectionRule.SQL_PATTERNS
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_for_database(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary data for database operations."""
        sanitized = {}
        sanitizer = SanitizeRule('data')
        
        for key, value in data.items():
            if isinstance(value, str):
                _, _, clean_value = sanitizer.validate(value)
                sanitized[key] = clean_value[:1000]  # Limit length
            else:
                sanitized[key] = value
        
        return sanitized


class DatabaseQueryValidator:
    """
    Whitelist-based database operation validator.
    Implements OWASP A03:2021 - Use parameterized queries.
    """
    
    ALLOWED_TABLES = [
        'depobangunan_products',
        'depobangunan_locations',
        'depobangunan_price_history'
    ]
    
    ALLOWED_COLUMNS = [
        'id', 'name', 'price', 'url', 'unit',
        'created_at', 'updated_at', 'code'
    ]
    
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """Validate table name against whitelist."""
        return table_name in DatabaseQueryValidator.ALLOWED_TABLES
    
    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        """Validate column name against whitelist."""
        return column_name in DatabaseQueryValidator.ALLOWED_COLUMNS
    
    @staticmethod
    def build_safe_query(
        operation: str,
        table: str,
        columns: list,
        where_clause: Optional[Dict] = None
    ) -> Tuple[bool, str, str]:
        """Build safe parameterized query."""
        # Validate operation
        if operation not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            return False, "Invalid operation", ""
        
        # Validate table
        if not DatabaseQueryValidator.validate_table_name(table):
            logger.critical(f"Invalid table name attempt: {table}")
            return False, "Invalid table name", ""
        
        # Validate columns
        for col in columns:
            if not DatabaseQueryValidator.validate_column_name(col):
                logger.critical(f"Invalid column name attempt: {col}")
                return False, "Invalid column name", ""
        
        # Build parameterized query
        if operation == 'SELECT':
            cols = ', '.join(columns)
            query = f"SELECT {cols} FROM {table}"
            if where_clause:
                query += " WHERE " + " AND ".join([f"{k} = %s" for k in where_clause.keys()])
        
        return True, "", query


# =============================================================================
# A04:2021 – Insecure Design Prevention
# =============================================================================

class BusinessRuleValidator:
    """
    Centralized business logic validation.
    Implements plausibility checks and domain constraints.
    """
    
    @staticmethod
    def validate_price(price: Any) -> Tuple[bool, str]:
        """Validate price with business rules."""
        if not isinstance(price, (int, float)) or price < 0:
            return False, "Price must be a positive number"
        
        if price > 1000000000:
            logger.warning(f"Suspicious price value: {price}")
            return False, "Price value exceeds reasonable limit"
        
        return True, ""
    
    @staticmethod
    def validate_product_name(name: str) -> Tuple[bool, str]:
        """Validate product name with business rules."""
        if len(name) < 2:
            return False, "Product name too short"
        
        if len(name) > 500:
            return False, "Product name too long"
        
        return True, ""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """Validate URL with SSRF protection."""
        if not url.startswith('https://'):
            return False, "URL must use HTTPS protocol for security"
        
        # SSRF protection
        dangerous_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
        if any(host in url for host in dangerous_hosts):
            logger.critical(f"SSRF attempt detected: {url}")
            return False, "Invalid URL"
        
        return True, ""


class SecurityDesignPatterns:
    """
    Implements secure design patterns and business logic validation.
    Implements OWASP A04:2021 - Insecure Design prevention.
    """
    
    # Validation registry maps field names to validators
    FIELD_VALIDATORS = {
        'price': BusinessRuleValidator.validate_price,
        'name': BusinessRuleValidator.validate_product_name,
        'url': BusinessRuleValidator.validate_url
    }
    
    @staticmethod
    def validate_business_logic(data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate data against business rules.
        Iterates through registered validators.
        """
        for field_name, validator in SecurityDesignPatterns.FIELD_VALIDATORS.items():
            if field_name in data:
                is_valid, error = validator(data[field_name])
                if not is_valid:
                    return False, error
        
        return True, ""
    
    # Legacy individual validators for backward compatibility
    @staticmethod
    def _validate_price_field(price: Any) -> Tuple[bool, str]:
        return BusinessRuleValidator.validate_price(price)
    
    @staticmethod
    def _validate_name_field(name: str) -> Tuple[bool, str]:
        return BusinessRuleValidator.validate_product_name(name)
    
    @staticmethod
    def _validate_url_field(url: str) -> Tuple[bool, str]:
        return BusinessRuleValidator.validate_url(url)
    
    @staticmethod
    def enforce_resource_limits(request, max_page_size: int = 100) -> Tuple[bool, str]:
        """Enforce resource consumption limits."""
        # Validate page size
        if 'limit' in request.GET:
            try:
                limit = int(request.GET['limit'])
                if limit > max_page_size:
                    return False, f"Limit exceeds maximum of {max_page_size}"
            except ValueError:
                return False, "Invalid limit parameter"
        
        # Validate query complexity
        param_count = len(request.GET)
        if param_count > 20:
            logger.warning(f"Excessive query parameters: {param_count}")
            return False, "Too many query parameters"
        
        return True, ""


# =============================================================================
# Security Decorators
# =============================================================================

def require_api_token(required_permission: str = None):
    """
    Decorator for API token authentication and authorization.
    Implements OWASP A01:2021 - Access control in server-side code.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Token validation
            is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
            
            if not is_valid:
                AccessControlManager.log_access_attempt(request, False, error_msg)
                return JsonResponse({'error': error_msg}, status=401)
            
            # Permission check
            if required_permission and not AccessControlManager.check_permission(
                token_info, required_permission
            ):
                AccessControlManager.log_access_attempt(
                    request, False, f"Missing permission: {required_permission}"
                )
                return JsonResponse({
                    'error': f'Insufficient permissions. Required: {required_permission}'
                }, status=403)
            
            # Rate limiting
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            client_id = f"{client_ip}:{request.path}"
            
            rate_config = token_info.get('rate_limit', {})
            max_reqs = rate_config.get('requests', 100)
            window = rate_config.get('window', 60)
            
            is_allowed, rate_error = rate_limiter.check_rate_limit(
                client_id, max_reqs, window
            )
            
            if not is_allowed:
                AccessControlManager.log_access_attempt(request, False, rate_error)
                return JsonResponse({'error': rate_error}, status=429)
            
            # Log success
            AccessControlManager.log_access_attempt(request, True)
            
            # Attach token info to request
            request.token_info = token_info
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


class RequestDataExtractor:
    """Extracts and validates request data."""
    
    @staticmethod
    def extract(request):
        """Extract data from request based on method."""
        if request.method == 'GET':
            return request.GET, None
        
        try:
            data = json.loads(request.body) if request.body else {}
            return data, None
        except json.JSONDecodeError:
            return None, JsonResponse({
                'error': 'Invalid JSON in request body'
            }, status=400)


class FieldValidationExecutor:
    """Executes validation functions on fields."""
    
    @staticmethod
    def validate_all(validators: Dict[str, Callable], data_source) -> Tuple[Dict, Dict]:
        """Execute all validators and collect results."""
        errors = {}
        validated_data = {}
        
        for field_name, validator_func in validators.items():
            value = data_source.get(field_name)
            is_valid, error_msg, sanitized_value = validator_func(value)
            
            if not is_valid:
                errors[field_name] = error_msg
            elif sanitized_value is not None:
                validated_data[field_name] = sanitized_value
        
        return errors, validated_data


def validate_input(validators: Dict[str, Callable]):
    """
    Decorator for input validation.
    Implements OWASP A03:2021 - Positive server-side validation.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Extract data
            data_source, error_response = RequestDataExtractor.extract(request)
            if error_response:
                return error_response
            
            # Validate fields
            errors, validated_data = FieldValidationExecutor.validate_all(validators, data_source)
            
            if errors:
                return JsonResponse({
                    'error': 'Validation failed',
                    'details': errors
                }, status=400)
            
            request.validated_data = validated_data
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def enforce_resource_limits(view_func):
    """
    Decorator to enforce resource consumption limits.
    Implements OWASP A04:2021 - Limit resource consumption.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


# Legacy helper functions for backward compatibility
def _get_request_data(request):
    """Legacy helper - redirects to RequestDataExtractor."""
    return RequestDataExtractor.extract(request)


def _validate_fields(validators: Dict[str, Callable], data_source) -> Tuple[Dict, Dict]:
    """Legacy helper - redirects to FieldValidationExecutor."""
    return FieldValidationExecutor.validate_all(validators, data_source)
