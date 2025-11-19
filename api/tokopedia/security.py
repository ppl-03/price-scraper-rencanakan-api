"""
OWASP Security Module for Tokopedia API
Implements A01:2021 (Broken Access Control), A03:2021 (Injection), A04:2021 (Insecure Design)

Architecture:
- Configuration-driven security policies
- Functional validation pipeline
- Modular security components
"""
import logging
import os
import re
import time
from functools import wraps
from typing import Optional, Dict, Any, Tuple, Callable, List
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.core.cache import cache
import bleach

logger = logging.getLogger(__name__)


# =============================================================================
# Security Configuration
# =============================================================================

SECURITY_CONFIG = {
    'rate_limiting': {
        'default_window': 60,
        'default_max_requests': 100,
        'block_duration': 300,
        'attack_threshold': 10
    },
    'validation': {
        'max_keyword_length': 100,
        'max_string_length': 1000,
        'max_query_params': 20,
        'max_page_size': 100
    },
    'business_logic': {
        'max_price': 1000000000,
        'min_name_length': 2,
        'max_name_length': 500
    },
    'ssrf_protection': {
        'blocked_hosts': [
            'localhost', 
            '127.0.0.1', 
            '0.0.0.0', 
            os.getenv('AWS_METADATA_IP', '169.254.169.254')
        ],
        'required_protocol': 'https://'
    }
}

# API Token Registry with enhanced metadata
TOKEN_REGISTRY = {
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

# SQL Injection patterns for detection
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
    r"(;|\-\-|\/\*|\*\/)",
    r"(\bOR\b.*=.*)",
    r"(\bAND\b.*=.*)",
    r"(\'|\"|`)",
]

# Whitelisted database identifiers
DB_WHITELIST = {
    'tables': {'tokopedia_products', 'tokopedia_locations', 'tokopedia_price_history'},
    'columns': {'id', 'name', 'price', 'url', 'unit', 'created_at', 'updated_at', 'code'},
    'operations': {'SELECT', 'INSERT', 'UPDATE', 'DELETE'}
}


# =============================================================================
# A01:2021 – Broken Access Control Prevention
# =============================================================================

class TokopediaRateLimitTracker:
    """
    Tokopedia-specific rate limiting with time-window based tracking.
    Uses sliding window algorithm for accurate rate limiting.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or SECURITY_CONFIG['rate_limiting']
        self._request_log = defaultdict(list)
        self._blocked_clients = {}
        
    def record_request(self, identifier: str) -> None:
        """Record a new request from client."""
        self._request_log[identifier].append(time.time())
        self._cleanup_old_entries(identifier)
    
    def _cleanup_old_entries(self, identifier: str) -> None:
        """Remove expired request records."""
        window = self._config['default_window']
        cutoff = time.time() - window
        self._request_log[identifier] = [
            ts for ts in self._request_log[identifier] if ts > cutoff
        ]
    
    def check_client_blocked(self, identifier: str) -> Tuple[bool, int]:
        """Check if client is currently blocked. Returns (is_blocked, remaining_seconds)."""
        if identifier not in self._blocked_clients:
            return False, 0
        
        unblock_time = self._blocked_clients[identifier]
        if time.time() >= unblock_time:
            del self._blocked_clients[identifier]
            return False, 0
        
        return True, int(unblock_time - time.time())
    
    def apply_block(self, identifier: str, duration: int = None) -> None:
        """Apply temporary block to client."""
        if duration is None:
            duration = self._config['block_duration']
        self._blocked_clients[identifier] = time.time() + duration
        logger.warning(f"Applied {duration}s block to client: {identifier}")
    
    def get_request_count(self, identifier: str) -> int:
        """Get current request count in active window."""
        self._cleanup_old_entries(identifier)
        return len(self._request_log[identifier])
    
    def evaluate_limit(
        self, 
        identifier: str, 
        max_requests: int = None,
        auto_block: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if client is within rate limits.
        
        Returns:
            (allowed, error_message)
        """
        # Check if blocked
        is_blocked, remaining = self.check_client_blocked(identifier)
        if is_blocked:
            return False, f"Access temporarily blocked. Retry in {remaining} seconds"
        
        # Get configuration
        max_req = max_requests or self._config['default_max_requests']
        
        # Check current usage
        current_count = self.get_request_count(identifier)
        
        if current_count >= max_req:
            if auto_block:
                self.apply_block(identifier)
            
            logger.warning(f"Rate limit exceeded: {identifier} ({current_count} requests)")
            return False, f"Rate limit exceeded. Max {max_req} requests per {self._config['default_window']}s"
        
        # Record this request
        self.record_request(identifier)
        return True, None


# Initialize rate limit tracker
_rate_tracker = TokopediaRateLimitTracker()


class TokopediaAccessControl:
    """
    Token-based access control with permission management.
    Implements OWASP A01:2021 - Centralized access control enforcement.
    """
    
    @staticmethod
    def extract_token(request) -> Optional[str]:
        """Extract authentication token from request headers."""
        token = request.headers.get('X-API-Token')
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')
        return token
    
    @staticmethod
    def lookup_token(token: str) -> Optional[Dict]:
        """Lookup token in registry."""
        return TOKEN_REGISTRY.get(token)
    
    @staticmethod
    def verify_ip_whitelist(client_ip: str, token_data: Dict) -> bool:
        """Verify client IP against token whitelist."""
        allowed_ips = token_data.get('allowed_ips', [])
        if not allowed_ips:  # Empty list means all IPs allowed
            return True
        return client_ip in allowed_ips
    
    @classmethod
    def authenticate_request(cls, request) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate request using token-based auth.
        
        Returns:
            (is_valid, error_message, token_data)
        """
        # Extract and validate token
        token = cls.extract_token(request)
        if not token:
            return False, 'API token required', None
        
        token_data = cls.lookup_token(token)
        if not token_data:
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            logger.warning(f"Invalid token attempt from {client_ip}")
            return False, 'Invalid API token', None
        
        # Verify IP restrictions
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        if not cls.verify_ip_whitelist(client_ip, token_data):
            logger.warning(f"IP {client_ip} denied for token: {token_data['name']}")
            return False, 'IP not authorized for this token', None
        
        # Check expiration (if implemented)
        if token_data.get('expires'):
            # Future: Add expiration check
            pass
        
        logger.info(f"Authenticated: {token_data['name']} from {client_ip}")
        return True, '', token_data
    
    @staticmethod
    def has_permission(token_data: Dict, required: str) -> bool:
        """
        Check if token grants required permission.
        Implements least privilege principle.
        """
        granted = token_data.get('permissions', [])
        has_access = required in granted
        
        if not has_access:
            logger.warning(f"Permission '{required}' denied for {token_data['name']}")
        
        return has_access
    
    @staticmethod
    def sanitize_log_data(value: str, max_len: int = 200) -> str:
        """Sanitize data for safe logging (prevent log injection)."""
        if not value:
            return 'unknown'
        truncated = str(value)[:max_len]
        return ''.join(c if c.isprintable() else '' for c in truncated)
    
    @classmethod
    def audit_access(cls, request, granted: bool, reason: str = '') -> None:
        """
        Audit log for access control decisions.
        Implements OWASP A01:2021 - Log access control failures.
        """
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        safe_path = cls.sanitize_log_data(request.path)
        safe_reason = cls.sanitize_log_data(reason, 100)
        timestamp = datetime.now().isoformat()
        
        log_entry = (
            f"{'GRANTED' if granted else 'DENIED'} - "
            f"IP: {client_ip}, Path: {safe_path}, Method: {request.method}, "
            f"Time: {timestamp}"
        )
        
        if granted:
            logger.info(log_entry)
        else:
            logger.warning(f"{log_entry}, Reason: {safe_reason}")
            cls.detect_attack_pattern(client_ip)
    
    @staticmethod
    def detect_attack_pattern(client_ip: str) -> None:
        """
        Detect potential attack patterns based on failed attempts.
        """
        cache_key = f"tokopedia_failed_auth_{client_ip}"
        failure_count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, failure_count, 300)
        
        threshold = SECURITY_CONFIG['rate_limiting']['attack_threshold']
        if failure_count > threshold:
            logger.critical(
                f"SECURITY ALERT: Potential attack detected from {client_ip}. "
                f"Failed attempts: {failure_count}"
            )
            # Production: Alert admins, consider blocking


# =============================================================================
# A03:2021 – Injection Prevention
# =============================================================================

class ValidationPipeline:
    """
    Functional validation pipeline for input sanitization.
    Implements OWASP A03:2021 - Input validation and sanitization.
    """
    
    # Compiled regex patterns for validation
    PATTERNS = {
        'keyword': re.compile(r'^[a-zA-Z0-9\s\-_\.]+$'),
        'numeric': re.compile(r'^\d+$'),
        'boolean': re.compile(r'^(true|false|1|0|yes|no)$', re.IGNORECASE)
    }
    
    @staticmethod
    def check_sql_injection(value: str) -> bool:
        """Detect SQL injection patterns."""
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def validate_keyword_field(
        cls, 
        keyword: str, 
        max_length: int = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate keyword with whitelist pattern matching.
        
        Returns:
            (is_valid, error_message, sanitized_value)
        """
        if not keyword:
            return False, "Keyword is required", None
        
        max_len = max_length or SECURITY_CONFIG['validation']['max_keyword_length']
        
        if len(keyword) > max_len:
            return False, f"Keyword exceeds maximum length of {max_len}", None
        
        keyword = keyword.strip()
        if not keyword:
            return False, "Keyword cannot be empty", None
        
        # Whitelist pattern check
        if not cls.PATTERNS['keyword'].match(keyword):
            logger.warning(f"Invalid keyword pattern: {keyword}")
            return False, "Keyword contains invalid characters", None
        
        # SQL injection check
        if cls.check_sql_injection(keyword):
            logger.critical(f"SQL injection attempt: {keyword}")
            return False, "Invalid keyword format", None
        
        # HTML sanitization
        sanitized = bleach.clean(keyword, tags=[], strip=True)
        return True, "", sanitized
    
    @classmethod
    def validate_integer_field(
        cls,
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Validate and convert integer with range checking.
        """
        if value is None:
            return False, f"{field_name} is required", None
        
        # Type conversion
        if isinstance(value, int):
            converted = value
        elif isinstance(value, str):
            if not cls.PATTERNS['numeric'].match(value):
                return False, f"{field_name} must be a valid integer", None
            try:
                converted = int(value)
            except ValueError:
                return False, f"{field_name} must be a valid integer", None
        else:
            return False, f"{field_name} must be an integer", None
        
        # Range validation
        if min_value is not None and converted < min_value:
            return False, f"{field_name} must be at least {min_value}", None
        if max_value is not None and converted > max_value:
            return False, f"{field_name} must be at most {max_value}", None
        
        return True, "", converted
    
    @classmethod
    def validate_boolean_field(
        cls,
        value: Any,
        field_name: str
    ) -> Tuple[bool, str, Optional[bool]]:
        """
        Validate boolean field.
        """
        if value is None:
            return True, "", None
        
        if value == '':
            return False, f"{field_name} must be a boolean value", None
        
        if isinstance(value, bool):
            return True, "", value
        
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ['true', '1', 'yes']:
                return True, "", True
            if lower_val in ['false', '0', 'no']:
                return True, "", False
        
        return False, f"{field_name} must be a boolean value", None
    
    @staticmethod
    def sanitize_for_db(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data before database operations.
        """
        sanitized = {}
        max_len = SECURITY_CONFIG['validation']['max_string_length']
        
        for key, value in data.items():
            if isinstance(value, str):
                value = value.replace('\x00', '')
                value = value[:max_len]
                value = bleach.clean(value, tags=[], strip=True)
            sanitized[key] = value
        
        return sanitized


class DatabaseSecurityValidator:
    """
    Database query validator using whitelist approach.
    Implements OWASP A03:2021 - Parameterized queries.
    """
    
    @staticmethod
    def is_valid_table(table_name: str) -> bool:
        """Validate table name against whitelist."""
        if table_name not in DB_WHITELIST['tables']:
            logger.critical(f"Invalid table access attempt: {table_name}")
            return False
        return True
    
    @staticmethod
    def is_valid_column(column_name: str) -> bool:
        """Validate column name against whitelist."""
        if column_name not in DB_WHITELIST['columns']:
            logger.critical(f"Invalid column access attempt: {column_name}")
            return False
        return True
    
    @staticmethod
    def is_valid_operation(operation: str) -> bool:
        """Validate database operation."""
        return operation in DB_WHITELIST['operations']
    
    @classmethod
    def construct_safe_query(
        cls,
        operation: str,
        table: str,
        columns: List[str],
        where_clause: Optional[Dict] = None
    ) -> Tuple[bool, str, str]:
        """
        Construct safe parameterized query.
        
        Returns:
            (is_valid, error_message, query)
        """
        if not cls.is_valid_operation(operation):
            return False, "Invalid operation", ""
        
        if not cls.is_valid_table(table):
            return False, "Invalid table name", ""
        
        for col in columns:
            if not cls.is_valid_column(col):
                return False, f"Invalid column: {col}", ""
        
        # Build query
        if operation == 'SELECT':
            cols = ', '.join(columns)
            query = f"SELECT {cols} FROM {table}"
            if where_clause:
                query += " WHERE " + " AND ".join([f"{k} = %s" for k in where_clause.keys()])
        else:
            # Add other operations as needed
            return False, "Operation not implemented", ""
        
        return True, "", query


# =============================================================================
# A04:2021 – Insecure Design Prevention
# =============================================================================

class BusinessLogicValidator:
    """
    Business logic validation with security constraints.
    Implements OWASP A04:2021 - Secure design patterns.
    """
    
    # SSRF Protection: Blocked hosts for URL validation
    SSRF_BLOCKED_HOSTS = SECURITY_CONFIG['ssrf_protection']['blocked_hosts']
    
    @staticmethod
    def validate_price(price: Any) -> Tuple[bool, str]:
        """Validate price field."""
        max_price = SECURITY_CONFIG['business_logic']['max_price']
        
        if not isinstance(price, (int, float)) or price < 0:
            return False, "Price must be a positive number"
        
        if price > max_price:
            logger.warning(f"Suspicious price value: {price}")
            return False, f"Price exceeds maximum limit of {max_price}"
        
        return True, ""
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """Validate name field."""
        min_len = SECURITY_CONFIG['business_logic']['min_name_length']
        max_len = SECURITY_CONFIG['business_logic']['max_name_length']
        
        if len(name) > max_len:
            return False, f"Name too long (max: {max_len})"
        if len(name) < min_len:
            return False, f"Name too short (min: {min_len})"
        
        return True, ""
    
    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """Validate URL with SSRF protection."""
        required_protocol = SECURITY_CONFIG['ssrf_protection']['required_protocol']
        
        if not url.startswith(required_protocol):
            return False, "URL must use HTTPS protocol"
        
        # SSRF protection
        url_lower = url.lower()
        for host in cls.SSRF_BLOCKED_HOSTS:
            if host in url_lower:
                logger.critical(f"SSRF attempt detected: {url}")
                return False, "Invalid URL"
        
        return True, ""
    
    @classmethod
    def validate_business_constraints(cls, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate business logic constraints.
        """
        validators = {
            'price': cls.validate_price,
            'name': cls.validate_name,
            'url': cls.validate_url
        }
        
        for field, validator in validators.items():
            if field in data:
                is_valid, error = validator(data[field])
                if not is_valid:
                    return False, error
        
        return True, ""
    
    @staticmethod
    def enforce_resource_constraints(request) -> Tuple[bool, str]:
        """
        Enforce resource consumption limits.
        """
        max_page = SECURITY_CONFIG['validation']['max_page_size']
        max_params = SECURITY_CONFIG['validation']['max_query_params']
        
        # Limit page size
        if 'limit' in request.GET:
            try:
                limit = int(request.GET['limit'])
                if limit > max_page:
                    return False, f"Limit exceeds maximum of {max_page}"
            except ValueError:
                return False, "Invalid limit parameter"
        
        # Limit query complexity
        if len(request.GET) > max_params:
            logger.warning(f"Excessive query parameters: {len(request.GET)}")
            return False, "Too many query parameters"
        
        return True, ""


# =============================================================================
# Security Decorators
# =============================================================================

def require_api_token(required_permission: str = None):
    """
    Decorator for API token authentication and authorization.
    
    Usage:
        @require_api_token(required_permission='scrape')
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            access_control = TokopediaAccessControl()
            
            # Authenticate
            is_valid, error_msg, token_data = access_control.authenticate_request(request)
            
            if not is_valid:
                access_control.audit_access(request, False, error_msg)
                return JsonResponse({'error': error_msg}, status=401)
            
            # Check permission
            if required_permission and not access_control.has_permission(token_data, required_permission):
                access_control.audit_access(request, False, f"Missing permission: {required_permission}")
                return JsonResponse({
                    'error': f'Insufficient permissions. Required: {required_permission}'
                }, status=403)
            
            # Rate limiting
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            client_id = f"{client_ip}:{request.path}"
            
            rate_config = token_data.get('rate_limit', {})
            max_req = rate_config.get('requests', 100)
            
            is_allowed, rate_error = _rate_tracker.evaluate_limit(client_id, max_req)
            
            if not is_allowed:
                access_control.audit_access(request, False, rate_error)
                return JsonResponse({'error': rate_error}, status=429)
            
            # Success
            access_control.audit_access(request, True)
            request.token_info = token_data
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def _extract_request_data(request):
    """Extract data from request based on method."""
    if request.method == 'GET':
        return request.GET, None
    
    try:
        import json
        data = json.loads(request.body) if request.body else {}
        return data, None
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'Invalid JSON in request body'}, status=400)


def _run_validators(validators: Dict[str, Callable], data_source) -> Tuple[Dict, Dict]:
    """Run validation pipeline."""
    errors = {}
    validated = {}
    
    for field, validator in validators.items():
        value = data_source.get(field)
        is_valid, error, sanitized = validator(value)
        
        if not is_valid:
            errors[field] = error
        elif sanitized is not None:
            validated[field] = sanitized
    
    return errors, validated


def validate_input(validators: Dict[str, Callable]):
    """
    Decorator for input validation.
    
    Usage:
        @validate_input({
            'keyword': lambda x: ValidationPipeline.validate_keyword_field(x),
            'page': lambda x: ValidationPipeline.validate_integer_field(x, 'page', min_value=0)
        })
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            data_source, error_resp = _extract_request_data(request)
            if error_resp:
                return error_resp
            
            errors, validated = _run_validators(validators, data_source)
            
            if errors:
                return JsonResponse({
                    'error': 'Validation failed',
                    'details': errors
                }, status=400)
            
            request.validated_data = validated
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def enforce_resource_limits(view_func):
    """
    Decorator to enforce resource consumption limits.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        is_valid, error_msg = BusinessLogicValidator.enforce_resource_constraints(request)
        
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view
