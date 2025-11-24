import logging
import re
import time
import json
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection
import bleach

logger = logging.getLogger(__name__)


# =============================================================================
# Common Utility Functions
# =============================================================================

def get_client_ip(request) -> str:
    """Extract client IP address from request."""
    return request.META.get('REMOTE_ADDR', 'unknown')


def sanitize_string(value: str, max_length: int = 200) -> str:
    """Sanitize string by removing non-printable characters and limiting length."""
    truncated = value[:max_length]
    return ''.join(c if c.isprintable() else '' for c in truncated)


# =============================================================================
# A01:2021 – Broken Access Control Prevention
# =============================================================================

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = {}
        
    def _clean_old_requests(self, client_id: str, window_seconds: int):
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff_time
        ]
    
    def is_blocked(self, client_id: str) -> bool:
        if client_id in self.blocked_ips:
            block_until = self.blocked_ips[client_id]
            if time.time() < block_until:
                return True
            else:
                del self.blocked_ips[client_id]
        return False
    
    def block_client(self, client_id: str, duration_seconds: int = 300):
        self.blocked_ips[client_id] = time.time() + duration_seconds
        logger.warning(f"Client {client_id} blocked for {duration_seconds} seconds due to rate limit violation")
    
    def check_rate_limit(
        self, 
        client_id: str, 
        max_requests: int = 100, 
        window_seconds: int = 60,
        block_on_violation: bool = True
    ) -> Tuple[bool, Optional[str]]:
        if self.is_blocked(client_id):
            remaining_time = int(self.blocked_ips[client_id] - time.time())
            return False, f"Rate limit exceeded. Blocked for {remaining_time} more seconds"
        
        self._clean_old_requests(client_id, window_seconds)
        
        current_requests = len(self.requests[client_id])
        
        if current_requests >= max_requests:
            if block_on_violation:
                self.block_client(client_id)
            logger.warning(
                f"Rate limit exceeded for {client_id}: "
                f"{current_requests} requests in {window_seconds}s window"
            )
            return False, f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds"
        
        self.requests[client_id].append(time.time())
        return True, None


rate_limiter = RateLimiter()


class AccessControlManager:
    API_TOKENS = {
        'mitra10-dev-token-12345': {
            'name': 'Mitra10 Development Token',
            'owner': 'dev-team',
            'permissions': ['read', 'write', 'scrape'],
            'allowed_ips': [],
            'rate_limit': {'requests': 100, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        },
        'mitra10-legacy-api-token-67890': {
            'name': 'Mitra10 Legacy Client Token',
            'owner': 'legacy-client',
            'permissions': ['read', 'scrape'],
            'allowed_ips': [],
            'rate_limit': {'requests': 50, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        },
        'mitra10-read-only-token': {
            'name': 'Mitra10 Read Only Token',
            'owner': 'monitoring',
            'permissions': ['read'],
            'allowed_ips': [],
            'rate_limit': {'requests': 200, 'window': 60},
            'created': '2024-01-01',
            'expires': None
        }
    }
    
    @classmethod
    def validate_token(cls, request) -> Tuple[bool, str, Optional[Dict]]:
        token = request.headers.get('X-API-Token') or \
                request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return False, 'API token required', None
        
        if token not in cls.API_TOKENS:
            client_ip = get_client_ip(request)
            logger.warning(f"Invalid API token attempt from {client_ip}")
            return False, 'Invalid API token', None
        
        token_info = cls.API_TOKENS[token]
        client_ip = get_client_ip(request)
        
        if token_info.get('expires') and datetime.now() > token_info['expires']:
            return False, 'Token expired', None
        
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
        permissions = token_info.get('permissions', [])
        has_permission = required_permission in permissions
        
        if not has_permission:
            logger.warning(
                f"Permission denied: {token_info['name']} lacks '{required_permission}' permission"
            )
        
        return has_permission
    
    @classmethod
    def log_access_attempt(cls, request, success: bool, reason: str = ''):
        client_ip = get_client_ip(request)
        path = sanitize_string(request.path)
        method = request.method
        safe_reason = sanitize_string(str(reason), 100) if reason else 'unknown'
        
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
            cls._check_for_attack_pattern(client_ip)
    
    @classmethod
    def _check_for_attack_pattern(cls, client_ip: str):
        cache_key = f"failed_access_mitra10_{client_ip}"
        failures = cache.get(cache_key, 0)
        failures += 1
        cache.set(cache_key, failures, 300)
        
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
    KEYWORD_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]+$')
    NUMERIC_PATTERN = re.compile(r'^\d+$')
    BOOLEAN_PATTERN = re.compile(r'^(true|false|1|0|yes|no)$', re.IGNORECASE)
    
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(;|\-\-|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(\'|\"|`)",
    ]
    
    @staticmethod
    def _create_validation_error(field_name: str, message: str) -> Tuple[bool, str, None]:
        """Helper to create consistent validation error responses."""
        return False, f"{field_name} {message}" if field_name else message, None
    
    @classmethod
    def validate_keyword(cls, keyword: str, max_length: int = 100) -> Tuple[bool, str, Optional[str]]:
        if not keyword:
            return False, "Keyword is required", None
        
        if len(keyword) > max_length:
            return False, f"Keyword exceeds maximum length of {max_length}", None
        
        keyword = keyword.strip()
        
        if not keyword:
            return False, "Keyword cannot be empty", None
        
        if not cls.KEYWORD_PATTERN.match(keyword):
            logger.warning(f"Invalid keyword pattern detected: {keyword}")
            return False, "Keyword contains invalid characters. Only alphanumeric, spaces, hyphens, underscores, and periods allowed", None
        
        if cls._detect_sql_injection(keyword):
            logger.critical(f"SQL injection attempt detected in keyword: {keyword}")
            return False, "Invalid keyword format", None
        
        sanitized = bleach.clean(keyword, tags=[], strip=True)
        
        return True, "", sanitized
    
    @classmethod
    def validate_integer(
        cls, 
        value: Any, 
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        if value is None:
            return cls._create_validation_error(field_name, "is required")
        
        if isinstance(value, str):
            if not cls.NUMERIC_PATTERN.match(value):
                return cls._create_validation_error(field_name, "must be a valid integer")
            try:
                value = int(value)
            except ValueError:
                return cls._create_validation_error(field_name, "must be a valid integer")
        elif not isinstance(value, int):
            return cls._create_validation_error(field_name, "must be an integer")
        
        if min_value is not None and value < min_value:
            return cls._create_validation_error(field_name, f"must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            return cls._create_validation_error(field_name, f"must be at most {max_value}")
        
        return True, "", value
    
    @classmethod
    def validate_boolean(cls, value: Any, field_name: str) -> Tuple[bool, str, Optional[bool]]:
        if value is None:
            return True, "", None
        
        if value == '':
            return cls._create_validation_error(field_name, "must be a boolean value")
        
        if isinstance(value, bool):
            return True, "", value
        
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ['true', '1', 'yes']:
                return True, "", True
            elif value_lower in ['false', '0', 'no']:
                return True, "", False
        
        return cls._create_validation_error(field_name, "must be a boolean value")
    
    @classmethod
    def _detect_sql_injection(cls, value: str) -> bool:
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_for_database(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                value = value.replace('\x00', '')
                value = value[:1000]
                value = bleach.clean(value, tags=[], strip=True)
            
            sanitized[key] = value
        
        return sanitized


class DatabaseQueryValidator:
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        allowed_tables = [
            'mitra10_products',
            'mitra10_locations',
            'mitra10_price_history'
        ]
        return table_name in allowed_tables
    
    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        allowed_columns = [
            'id', 'name', 'price', 'url', 'unit', 
            'created_at', 'updated_at', 'code', 'location'
        ]
        return column_name in allowed_columns
    
    @staticmethod
    def build_safe_query(
        operation: str,
        table: str,
        columns: list,
        where_clause: Optional[Dict] = None
    ) -> Tuple[bool, str, str]:
        if operation not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            return False, "Invalid operation", ""
        
        if not DatabaseQueryValidator.validate_table_name(table):
            logger.critical(f"Invalid table name attempt: {table}")
            return False, "Invalid table name", ""
        
        for col in columns:
            if not DatabaseQueryValidator.validate_column_name(col):
                logger.critical(f"Invalid column name attempt: {col}")
                return False, f"Invalid column name: {col}", ""
        
        if operation == 'SELECT':
            cols = ', '.join(columns)
            query = f"SELECT {cols} FROM {table}"
            
            if where_clause:
                where_parts = [f"{k} = %s" for k in where_clause.keys()]
                query += " WHERE " + " AND ".join(where_parts)
        
        else:
            return False, "Operation not implemented", ""
        
        return True, "", query


# =============================================================================
# A04:2021 – Insecure Design Prevention
# =============================================================================

class SecurityDesignPatterns:
    @staticmethod
    def _validate_price_lambda(price):
        if not isinstance(price, (int, float)) or price < 0:
            return (False, "Price must be a positive number")
        if price > 1000000000:
            logger.warning(f"Suspicious price value: {price}")
            return (False, "Price value exceeds reasonable limit")
        return (True, "")
    
    @staticmethod
    def _validate_name_lambda(name):
        if len(name) > 500:
            return (False, "Product name too long")
        if len(name) < 2:
            return (False, "Product name too short")
        return (True, "")
    
    @staticmethod
    def _validate_url_lambda(url):
        if not url.startswith('https://www.mitra10.com'):
            return (False, "URL must be from mitra10.com domain")
        if 'localhost' in url or '127.0.0.1' in url or '0.0.0.0' in url:
            logger.critical(f"SSRF attempt detected: {url}")
            return (False, "Invalid URL")
        return (True, "")
    
    FIELD_VALIDATORS = {
        'price': lambda price: SecurityDesignPatterns._validate_price_lambda(price),
        'name': lambda name: SecurityDesignPatterns._validate_name_lambda(name),
        'url': lambda url: SecurityDesignPatterns._validate_url_lambda(url)
    }
    
    @staticmethod
    def _validate_field(field_name: str, value: Any) -> Tuple[bool, str]:
        """Generic field validation using registered validators."""
        if field_name in SecurityDesignPatterns.FIELD_VALIDATORS:
            return SecurityDesignPatterns.FIELD_VALIDATORS[field_name](value)
        return True, ""
    
    @staticmethod
    def validate_business_logic(data: Dict[str, Any]) -> Tuple[bool, str]:
        for field_name in ['price', 'name', 'url']:
            if field_name in data:
                is_valid, error_msg = SecurityDesignPatterns._validate_field(field_name, data[field_name])
                if not is_valid:
                    return False, error_msg
        return True, ""
    
    @staticmethod
    def enforce_resource_limits(request, max_page_size: int = 100) -> Tuple[bool, str]:
        if 'limit' in request.GET:
            try:
                limit = int(request.GET['limit'])
                if limit > max_page_size:
                    return False, f"Limit exceeds maximum of {max_page_size}"
            except ValueError:
                return False, "Invalid limit parameter"
        
        query_params_count = len(request.GET)
        if query_params_count > 20:
            logger.warning(f"Excessive query parameters: {query_params_count}")
            return False, "Too many query parameters"
        
        return True, ""


# =============================================================================
# Security Decorators
# =============================================================================

def require_api_token(required_permission: str = 'read'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            is_valid, error_msg, token_info = AccessControlManager.validate_token(request)
            
            if not is_valid:
                AccessControlManager.log_access_attempt(request, False, error_msg)
                return JsonResponse({
                    'error': error_msg,
                    'code': 'AUTHENTICATION_FAILED'
                }, status=401)
            
            if not AccessControlManager.check_permission(token_info, required_permission):
                AccessControlManager.log_access_attempt(
                    request, False, f"Missing {required_permission} permission"
                )
                return JsonResponse({
                    'error': f"Insufficient permissions. Required: {required_permission}",
                    'code': 'AUTHORIZATION_FAILED'
                }, status=403)
            
            client_ip = get_client_ip(request)
            endpoint = request.path
            client_id = f"{client_ip}:{endpoint}"
            
            rate_config = token_info.get('rate_limit', {'requests': 100, 'window': 60})
            is_allowed, rate_error = rate_limiter.check_rate_limit(
                client_id,
                max_requests=rate_config['requests'],
                window_seconds=rate_config['window']
            )
            
            if not is_allowed:
                AccessControlManager.log_access_attempt(request, False, rate_error)
                return JsonResponse({
                    'error': rate_error,
                    'code': 'RATE_LIMIT_EXCEEDED'
                }, status=429)
            
            AccessControlManager.log_access_attempt(request, True)
            
            request.token_info = token_info
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def validate_input(validators: dict):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # For POST, check both query params and body
            if request.method == 'POST':
                try:
                    if request.content_type == 'application/json':
                        data_source = {**request.GET.dict(), **json.loads(request.body)}
                    else:
                        data_source = {**request.GET.dict(), **request.POST.dict()}
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to parse request body: {str(e)}")
                    data_source = {**request.GET.dict(), **request.POST.dict()}
            else:
                data_source = request.GET
            
            errors = {}
            validated_data = {}
            
            for field_name, validator_func in validators.items():
                value = data_source.get(field_name)
                is_valid, error_msg, validated_value = validator_func(value)
                
                if not is_valid:
                    errors[field_name] = error_msg
                    logger.warning(f"Validation failed for {field_name}: {error_msg}")
                else:
                    validated_data[field_name] = validated_value
            
            if errors:
                return JsonResponse({
                    'error': 'Validation failed',
                    'details': errors
                }, status=400)
            
            request.validated_data = validated_data
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def enforce_resource_limits(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_valid, error_msg = SecurityDesignPatterns.enforce_resource_limits(request)
        
        if not is_valid:
            logger.warning(f"Resource limit violation: {error_msg} from {request.META.get('REMOTE_ADDR')}")
            return JsonResponse(
                {'error': error_msg, 'code': 'RESOURCE_LIMIT_EXCEEDED'},
                status=400
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def secure_endpoint(required_permission: str = 'read'):
    def decorator(view_func):
        secured_func = validate_input(view_func)
        secured_func = require_api_token(required_permission)(secured_func)
        return secured_func
    return decorator
