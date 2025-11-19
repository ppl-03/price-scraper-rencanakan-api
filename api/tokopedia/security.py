"""
OWASP Security Module for Tokopedia API
Implements A01:2021 (Broken Access Control)
"""
import logging
import time
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.core.cache import cache

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
    def log_access_attempt(cls, request, success: bool, reason: str = ''):
        """
        Log access control events for monitoring and alerting.
        Implements OWASP A01:2021 - Log access control failures.
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


def enforce_resource_limits(view_func):
    """
    Decorator to enforce resource consumption limits.
    Implements OWASP A04:2021 - Limit resource consumption.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Limit page size for pagination
        if 'limit' in request.GET:
            try:
                limit = int(request.GET['limit'])
                if limit > 1000:
                    return JsonResponse({
                        'success': False,
                        'error_message': 'Limit parameter must not exceed 1000 for security reasons'
                    }, status=400)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error_message': 'Invalid limit parameter'
                }, status=400)
        
        # Limit query complexity
        query_params_count = len(request.GET)
        if query_params_count > 20:
            logger.warning(f"Excessive query parameters: {query_params_count}")
            return JsonResponse({
                'success': False,
                'error_message': 'Too many query parameters'
            }, status=400)
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view
