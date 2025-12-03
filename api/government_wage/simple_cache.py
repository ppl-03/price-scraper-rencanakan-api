"""
Simple in-memory cache for government wage data.
This module provides a basic caching mechanism to avoid repeated scraping.
"""
import hashlib
from typing import Any, Optional


# Simple in-memory cache dictionary
_cache = {}


def make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key from arguments.
    
    Args:
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key
    
    Returns:
        A string cache key
    """
    # Convert all arguments to strings and join them
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    # Create a hash of the combined key parts using SHA-256 (secure hash algorithm)
    key_string = ":".join(key_parts)
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()
    
    return f"gov_wage:{key_hash}"


def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from the cache.
    
    Args:
        key: The cache key to retrieve
    
    Returns:
        The cached value if it exists, None otherwise
    """
    return _cache.get(key)


def set_cache(key: str, value: Any, timeout: Optional[int] = None) -> None:
    """
    Set a value in the cache.
    
    Args:
        key: The cache key
        value: The value to cache
        timeout: Optional timeout in seconds (not implemented in simple version)
    """
    _cache[key] = value


def delete_cache(key: str) -> None:
    """
    Delete a value from the cache.
    
    Args:
        key: The cache key to delete
    """
    if key in _cache:
        del _cache[key]


def clear_cache() -> None:
    """
    Clear all cached values.
    """
    _cache.clear()


def get_cache_stats() -> dict:
    """
    Get statistics about the cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        'size': len(_cache),
        'keys': list(_cache.keys())
    }
