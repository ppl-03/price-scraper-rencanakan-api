"""
Simple in-memory cache for government wage data
Works without Django cache settings
"""
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
import threading

logger = logging.getLogger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache"""
    
    def __init__(self, default_timeout: int = 900):
        self.default_timeout = default_timeout
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self._lock:
            if key not in self._cache:
                return None
                
            value, expiry_time = self._cache[key]
            
            # Check if expired
            if time.time() > expiry_time:
                del self._cache[key]
                return None
                
            return value
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set item in cache"""
        timeout = timeout or self.default_timeout
        expiry_time = time.time() + timeout
        
        with self._lock:
            self._cache[key] = (value, expiry_time)
    
    def clear(self) -> None:
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            current_time = time.time()
            valid_keys = sum(1 for _, expiry in self._cache.values() if expiry > current_time)
            return {
                'total_keys': len(self._cache),
                'valid_keys': valid_keys,
                'expired_keys': len(self._cache) - valid_keys
            }


# Global cache instance
_cache_instance = None
_cache_lock = threading.Lock()


def get_cache() -> SimpleCache:
    """Get or create cache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = SimpleCache(default_timeout=900)  # 15 minutes
                logger.info("Initialized simple cache for government wage API")
    
    return _cache_instance


def make_cache_key(prefix: str, data: str) -> str:
    """Create a cache key"""
    hash_value = hashlib.md5(data.encode()).hexdigest()
    return f"gov_wage_{prefix}_{hash_value}"