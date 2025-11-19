"""
OWASP Security Module for Tokopedia API
Implements A01:2021 (Broken Access Control), A03:2021 (Injection), A04:2021 (Insecure Design)
"""
import logging
import re
import time
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.core.cache import cache
import bleach

logger = logging.getLogger(__name__)


# =============================================================================
# A01:2021 – Broken Access Control Prevention
# =============================================================================

class RateLimiter:
    """
    Rate limiting implementation to prevent automated attacks.
    Implements OWASP A01:2021 - Rate limit API and controller access.
    """
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = {}
        
    def _clean_old_requests(self, client_id: str, window_seconds: int):
        """Remove requests older than the time window."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff_time
        ]
    
    def is_blocked(self, client_id: str) -> bool:
        """Check if client is currently blocked."""
        if client_id in self.blocked_ips:
            block_until = self.blocked_ips[client_id]
            if time.time() < block_until:
                return True
            else:
                del self.blocked_ips[client_id]
        return False
    
    def block_client(self, client_id: str, duration_seconds: int = 300):
        """Block a client for specified duration (default 5 minutes)."""
        self.blocked_ips[client_id] = time.time() + duration_seconds
        logger.warning(f"Client {client_id} blocked for {duration_seconds} seconds due to rate limit violation")
    
    def check_rate_limit(
        self, 
        client_id: str, 
        max_requests: int = 100, 
        window_seconds: int = 60,
        block_on_violation: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Unique identifier for the client (IP + endpoint)
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
            block_on_violation: Whether to block client on violation
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check if client is blocked
        if self.is_blocked(client_id):
            remaining_time = int(self.blocked_ips[client_id] - time.time())
            return False, f"Rate limit exceeded. Blocked for {remaining_time} more seconds"
        
        # Clean old requests
        self._clean_old_requests(client_id, window_seconds)
        
        # Check rate limit
        current_requests = len(self.requests[client_id])
        
        if current_requests >= max_requests:
            if block_on_violation:
                self.block_client(client_id)
            logger.warning(
                f"Rate limit exceeded for {client_id}: "
                f"{current_requests} requests in {window_seconds}s window"
            )
            return False, f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds"
        
        # Add current request
        self.requests[client_id].append(time.time())
        return True, None


# Global rate limiter instance
rate_limiter = RateLimiter()


class AccessControlManager:
    """
    Centralized access control management.
    Implements OWASP A01:2021 - Deny by default, enforce ownership.
    """
    
    # Token configuration with ownership and permissions
    API_TOKENS = {
        'dev-token-12345': {
            'name': 'Development Token',
            'owner': 'dev-team',
            'permissions': ['read', 'write', 'scrape'],
            'allowed_ips': [],  # Empty means all IPs allowed
            'rate_limit': {'requests': 100, 'window': 60},  # 100 req/min
            'created': '2024-01-01',
            'expires': None
        },
        'legacy-api-token-67890': {
            'name': 'Legacy Client Token',
            'owner': 'legacy-client',
            'permissions': ['read', 'scrape'],  # Limited permissions
            'allowed_ips': [],
            'rate_limit': {'requests': 50, 'window': 60},  # 50 req/min
            'created': '2024-01-01',
            'expires': None
        },
        'read-only-token': {
            'name': 'Read Only Token',
            'owner': 'monitoring',
            'permissions': ['read'],  # Read-only access
            'allowed_ips': [],
            'rate_limit': {'requests': 200, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        }
    }
    
    @classmethod
    def validate_token(cls, request) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate API token with comprehensive checks.
        
        Returns:
            Tuple of (is_valid, error_message, token_info)
        """
        # Extract token
        token = request.headers.get('X-API-Token') or \
                request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return False, 'API token required', None
        
        # Validate token exists
        if token not in cls.API_TOKENS:
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            logger.warning(f"Invalid API token attempt from {client_ip}")
            return False, 'Invalid API token', None
        
        token_info = cls.API_TOKENS[token]
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Check expiration
        if token_info.get('expires'):
            # In production, implement proper date checking
            pass
        
        # Check IP whitelist (deny by default if list is specified)
        allowed_ips = token_info.get('allowed_ips', [])
        if allowed_ips and client_ip not in allowed_ips:
            logger.warning(
                f"IP {client_ip} not authorized for token {token_info['name']}"
            )
            return False, 'IP not authorized for this token', None
        
        logger.info(f"Valid API token used from {client_ip}: {token_info['name']}")
        return True, '', token_info
    
    @classmethod
    def check_permission(cls, token_info: Dict, required_permission: str) -> bool:
        """
        Check if token has required permission.
        Implements principle of least privilege.
        """
        permissions = token_info.get('permissions', [])
        has_permission = required_permission in permissions
        
        if not has_permission:
            logger.warning(
                f"Permission denied: {token_info['name']} lacks '{required_permission}' permission"
            )
        
        return has_permission
    
    @classmethod
    def _sanitize_log_value(cls, value: str, max_length: int = 200) -> str:
        """Sanitize a value for safe logging."""
        if not value:
            return 'unknown'
        truncated = str(value)[:max_length]
        return ''.join(c if c.isprintable() else '' for c in truncated)
    
    @classmethod
    def log_access_attempt(cls, request, success: bool, reason: str = ''):
        """
        Log access control events for monitoring and alerting.
        Implements OWASP A01:2021 - Log access control failures.
        """
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        # Sanitize all user-controlled data to prevent log injection
        path = cls._sanitize_log_value(request.path)
        method = request.method
        safe_reason = cls._sanitize_log_value(reason, max_length=100)
        
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


# =============================================================================
# A03:2021 – Injection Prevention
# =============================================================================

class InputValidator:
    """
    Comprehensive input validation to prevent injection attacks.
    Implements OWASP A03:2021 - Keep data separate from commands.
    """
    
    # Whitelist patterns for common inputs
    KEYWORD_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]+$')
    NUMERIC_PATTERN = re.compile(r'^\d+$')
    BOOLEAN_PATTERN = re.compile(r'^(true|false|1|0|yes|no)$', re.IGNORECASE)
    
    # SQL injection detection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(;|\-\-|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(\'|\"|`)",
    ]
    
    @classmethod
    def validate_keyword(cls, keyword: str, max_length: int = 100) -> Tuple[bool, str, Optional[str]]:
        """
        Validate and sanitize keyword input.
        
        Returns:
            Tuple of (is_valid, error_message, sanitized_value)
        """
        if not keyword:
            return False, "Keyword is required", None
        
        # Length validation
        if len(keyword) > max_length:
            return False, f"Keyword exceeds maximum length of {max_length}", None
        
        # Strip whitespace
        keyword = keyword.strip()
        
        if not keyword:
            return False, "Keyword cannot be empty", None
        
        # Whitelist validation - only allow safe characters
        if not cls.KEYWORD_PATTERN.match(keyword):
            logger.warning(f"Invalid keyword pattern detected: {keyword}")
            return False, "Keyword contains invalid characters. Only alphanumeric, spaces, hyphens, underscores, and periods allowed", None
        
        # SQL injection detection
        if cls._detect_sql_injection(keyword):
            logger.critical(f"SQL injection attempt detected in keyword: {keyword}")
            return False, "Invalid keyword format", None
        
        # HTML sanitization (defense in depth)
        sanitized = bleach.clean(keyword, tags=[], strip=True)
        
        return True, "", sanitized
    
    @classmethod
    def _convert_to_integer(cls, value: Any, field_name: str) -> Tuple[bool, str, Optional[int]]:
        """Convert value to integer with validation."""
        if isinstance(value, int):
            return True, "", value
        
        if isinstance(value, str):
            if not cls.NUMERIC_PATTERN.match(value):
                return False, f"{field_name} must be a valid integer", None
            try:
                return True, "", int(value)
            except ValueError:
                return False, f"{field_name} must be a valid integer", None
        
        return False, f"{field_name} must be an integer", None
    
    @classmethod
    def _validate_range(cls, value: int, field_name: str, min_value: Optional[int], 
                        max_value: Optional[int]) -> Tuple[bool, str]:
        """Validate value is within specified range."""
        if min_value is not None and value < min_value:
            return False, f"{field_name} must be at least {min_value}"
        if max_value is not None and value > max_value:
            return False, f"{field_name} must be at most {max_value}"
        return True, ""
    
    @classmethod
    def validate_integer(
        cls, 
        value: Any, 
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Validate integer input with range checking.
        """
        if value is None:
            return False, f"{field_name} is required", None
        
        # Type checking and conversion
        is_valid, error_msg, converted_value = cls._convert_to_integer(value, field_name)
        if not is_valid:
            return False, error_msg, None
        
        # Range validation
        is_valid, error_msg = cls._validate_range(converted_value, field_name, min_value, max_value)
        if not is_valid:
            return False, error_msg, None
        
        return True, "", converted_value
    
    # Boolean value mappings
    TRUTHY_VALUES = {'true', '1', 'yes'}
    FALSY_VALUES = {'false', '0', 'no'}
    
    @classmethod
    def validate_boolean(cls, value: Any, field_name: str) -> Tuple[bool, str, Optional[bool]]:
        """
        Validate boolean input.
        """
        # Handle None and empty string
        if value is None:
            return True, "", None  # Return None to allow view to set default
        if value == '':
            return False, f"{field_name} must be a boolean value", None
        
        # Native boolean
        if isinstance(value, bool):
            return True, "", value
        
        # String conversion
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in cls.TRUTHY_VALUES:
                return True, "", True
            if value_lower in cls.FALSY_VALUES:
                return True, "", False
        
        return False, f"{field_name} must be a boolean value", None
    
    @classmethod
    def _detect_sql_injection(cls, value: str) -> bool:
        """
        Detect potential SQL injection patterns.
        """
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_for_database(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data before database operations.
        Implements parameterized queries pattern.
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Remove null bytes
                value = value.replace('\x00', '')
                # Limit length
                value = value[:1000]
                # HTML escape
                value = bleach.clean(value, tags=[], strip=True)
            
            sanitized[key] = value
        
        return sanitized


class DatabaseQueryValidator:
    """
    Validates database operations to prevent SQL injection.
    Implements OWASP A03:2021 - Use parameterized queries.
    """
    
    # Whitelist constants
    ALLOWED_TABLES = {
        'tokopedia_products',
        'tokopedia_locations',
        'tokopedia_price_history'
    }
    
    ALLOWED_COLUMNS = {
        'id', 'name', 'price', 'url', 'unit', 
        'created_at', 'updated_at', 'code'
    }
    
    @staticmethod
    def _validate_against_whitelist(value: str, whitelist: set, item_type: str) -> bool:
        """Generic whitelist validator."""
        if value not in whitelist:
            logger.critical(f"Invalid {item_type} attempt: {value}")
            return False
        return True
    
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """
        Validate table name against whitelist.
        Table names cannot be parameterized, so whitelist is critical.
        """
        return DatabaseQueryValidator._validate_against_whitelist(
            table_name, DatabaseQueryValidator.ALLOWED_TABLES, "table name"
        )
    
    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        """
        Validate column name against whitelist.
        """
        return DatabaseQueryValidator._validate_against_whitelist(
            column_name, DatabaseQueryValidator.ALLOWED_COLUMNS, "column name"
        )
    
    ALLOWED_OPERATIONS = {'SELECT', 'INSERT', 'UPDATE', 'DELETE'}
    
    @staticmethod
    def build_safe_query(
        operation: str,
        table: str,
        columns: list,
        where_clause: Optional[Dict] = None
    ) -> Tuple[bool, str, str]:
        """
        Build safe parameterized SQL query.
        
        Returns:
            Tuple of (is_valid, error_message, query)
        """
        # Validate operation
        if operation not in DatabaseQueryValidator.ALLOWED_OPERATIONS:
            return False, "Invalid operation", ""
        
        # Validate table name
        if not DatabaseQueryValidator.validate_table_name(table):
            return False, "Invalid table name", ""
        
        # Validate all column names
        for col in columns:
            if not DatabaseQueryValidator.validate_column_name(col):
                return False, "Invalid column name", ""
        
        # Build query based on operation
        if operation == 'SELECT':
            cols = ', '.join(columns)
            query = f"SELECT {cols} FROM {table}"
            if where_clause:
                # Use parameterized where clause
                query += " WHERE " + " AND ".join([f"{k} = %s" for k in where_clause.keys()])
        
        # Add more operations as needed
        
        return True, "", query


# =============================================================================
# A04:2021 – Insecure Design Prevention
# =============================================================================

class SecurityDesignPatterns:
    """
    Implements secure design patterns and best practices.
    Implements OWASP A04:2021 - Use secure design patterns.
    """
    
    @staticmethod
    def _validate_numeric_range(value: Any, field_name: str, min_val: float, max_val: float, 
                                log_suspicious: bool = False) -> Tuple[bool, str]:
        """Generic numeric range validator."""
        if not isinstance(value, (int, float)) or value < min_val:
            return False, f"{field_name} must be positive (at least {min_val})"
        if value > max_val:
            if log_suspicious:
                logger.warning(f"Suspicious {field_name} value: {value}")
            return False, f"{field_name} exceeds maximum limit of {max_val}"
        return True, ""
    
    @staticmethod
    def _validate_string_length(value: str, field_name: str, min_len: int, max_len: int) -> Tuple[bool, str]:
        """Generic string length validator."""
        if len(value) > max_len:
            return False, f"{field_name} too long (max: {max_len})"
        if len(value) < min_len:
            return False, f"{field_name} too short (min: {min_len})"
        return True, ""
    
    @staticmethod
    def _validate_price_field(price: Any) -> Tuple[bool, str]:
        """Validate price field in business logic."""
        return SecurityDesignPatterns._validate_numeric_range(
            price, "Price", 0, 1000000000, log_suspicious=True
        )
    
    @staticmethod
    def _validate_name_field(name: str) -> Tuple[bool, str]:
        """Validate name field in business logic."""
        return SecurityDesignPatterns._validate_string_length(name, "Product name", 2, 500)
    
    @staticmethod
    def _validate_url_field(url: str) -> Tuple[bool, str]:
        """Validate URL field with SSRF protection."""
        if not url.startswith('https://'):
            return False, "URL must use HTTPS protocol for security"
        
        # Check for SSRF attempts
        dangerous_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254']
        if any(host in url.lower() for host in dangerous_hosts):
            logger.critical(f"SSRF attempt detected: {url}")
            return False, "Invalid URL"
        return True, ""
    
    @staticmethod
    def validate_business_logic(data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate business logic constraints.
        Implements plausibility checks.
        """
        # Define field validators mapping
        field_validators = {
            'price': SecurityDesignPatterns._validate_price_field,
            'name': SecurityDesignPatterns._validate_name_field,
            'url': SecurityDesignPatterns._validate_url_field
        }
        
        # Validate each field present in data
        for field, validator in field_validators.items():
            if field in data:
                is_valid, error_msg = validator(data[field])
                if not is_valid:
                    return False, error_msg
        
        return True, ""
    
    @staticmethod
    def enforce_resource_limits(request, max_page_size: int = 100) -> Tuple[bool, str]:
        """
        Enforce resource consumption limits.
        Implements OWASP A04:2021 - Limit resource consumption.
        """
        # Limit page size
        if 'limit' in request.GET:
            try:
                limit = int(request.GET['limit'])
                if limit > max_page_size:
                    return False, f"Limit exceeds maximum of {max_page_size}"
            except ValueError:
                return False, "Invalid limit parameter"
        
        # Limit query complexity
        query_params_count = len(request.GET)
        if query_params_count > 20:
            logger.warning(f"Excessive query parameters: {query_params_count}")
            return False, "Too many query parameters"
        
        return True, ""


# =============================================================================
# Security Decorators
# =============================================================================

def require_api_token(required_permission: str = None):
    """
    Decorator for API token authentication and authorization.
    Implements OWASP A01:2021 - Access control in trusted server-side code.
    
    Usage:
        @require_api_token(required_permission='scrape')
        @require_http_methods(["GET"])
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Validate token
            is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
            
            if not is_valid:
                AccessControlManager.log_access_attempt(request, False, error_msg)
                return JsonResponse({'error': error_msg}, status=401)
            
            # Check permission if required
            if required_permission and not AccessControlManager.check_permission(
                token_info, required_permission
            ):
                AccessControlManager.log_access_attempt(
                    request, False, f"Missing permission: {required_permission}"
                )
                return JsonResponse({
                    'error': f'Insufficient permissions. Required: {required_permission}'
                }, status=403)
            
            # Check rate limit
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            client_id = f"{client_ip}:{request.path}"
            
            rate_limit_config = token_info.get('rate_limit', {})
            max_requests = rate_limit_config.get('requests', 100)
            window = rate_limit_config.get('window', 60)
            
            is_allowed, rate_error = rate_limiter.check_rate_limit(
                client_id, max_requests, window
            )
            
            if not is_allowed:
                AccessControlManager.log_access_attempt(request, False, rate_error)
                return JsonResponse({'error': rate_error}, status=429)
            
            # Log successful access
            AccessControlManager.log_access_attempt(request, True)
            
            # Attach token info to request for use in view
            request.token_info = token_info
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def _get_request_data(request):
    """Extract data source based on request method."""
    if request.method == 'GET':
        return request.GET, None
    
    try:
        import json
        data = json.loads(request.body) if request.body else {}
        return data, None
    except json.JSONDecodeError:
        return None, JsonResponse({
            'error': 'Invalid JSON in request body'
        }, status=400)


def _validate_fields(validators: Dict[str, callable], data_source) -> Tuple[Dict, Dict]:
    """Validate all fields and return errors and validated data."""
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


def validate_input(validators: Dict[str, callable]):
    """
    Decorator for input validation.
    Implements OWASP A03:2021 - Use positive server-side input validation.
    
    Usage:
        @validate_input({
            'keyword': lambda x: InputValidator.validate_keyword(x),
            'page': lambda x: InputValidator.validate_integer(x, 'page', min_value=0)
        })
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            data_source, error_response = _get_request_data(request)
            if error_response:
                return error_response
            
            errors, validated_data = _validate_fields(validators, data_source)
            
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
