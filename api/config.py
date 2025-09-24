import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ScraperConfig:
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    requests_per_minute: int = 60
    min_request_interval: float = 1.0
    
    cache_enabled: bool = True
    cache_ttl: int = 300
    
    log_level: str = 'INFO'
    log_requests: bool = True
    
    gemilang_base_url: str = 'https://gemilang-store.com'
    gemilang_search_path: str = '/pusat/shop'
    
    juragan_material_base_url: str = 'https://juraganmaterial.id'
    juragan_material_search_path: str = '/produk'

    depobangunan_base_url: str = 'https://www.depobangunan.co.id'
    depobangunan_search_path: str = '/catalogsearch/result/'
    
    @classmethod
    def from_environment(cls) -> 'ScraperConfig':
        return cls(
            request_timeout=int(os.getenv('SCRAPER_REQUEST_TIMEOUT', '30')),
            max_retries=int(os.getenv('SCRAPER_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('SCRAPER_RETRY_DELAY', '1.0')),
            user_agent=os.getenv('SCRAPER_USER_AGENT', cls.user_agent),
            requests_per_minute=int(os.getenv('SCRAPER_REQUESTS_PER_MINUTE', '60')),
            min_request_interval=float(os.getenv('SCRAPER_MIN_REQUEST_INTERVAL', '1.0')),
            cache_enabled=os.getenv('SCRAPER_CACHE_ENABLED', 'true').lower() == 'true',
            cache_ttl=int(os.getenv('SCRAPER_CACHE_TTL', '300')),
            log_level=os.getenv('SCRAPER_LOG_LEVEL', 'INFO'),
            log_requests=os.getenv('SCRAPER_LOG_REQUESTS', 'true').lower() == 'true',
            gemilang_base_url=os.getenv('GEMILANG_BASE_URL', 'https://gemilang-store.com'),
            gemilang_search_path=os.getenv('GEMILANG_SEARCH_PATH', '/pusat/shop'),
            juragan_material_base_url=os.getenv('JURAGAN_MATERIAL_BASE_URL', 'https://juraganmaterial.id'),
            juragan_material_search_path=os.getenv('JURAGAN_MATERIAL_SEARCH_PATH', '/produk'),
            depobangunan_base_url=os.getenv('DEPOBANGUNAN_BASE_URL', 'https://www.depobangunan.co.id'),
            depobangunan_search_path=os.getenv('DEPOBANGUNAN_SEARCH_PATH', '/catalogsearch/result/'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'request_timeout': self.request_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'user_agent': self.user_agent,
            'requests_per_minute': self.requests_per_minute,
            'min_request_interval': self.min_request_interval,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl,
            'log_level': self.log_level,
            'log_requests': self.log_requests,
            'gemilang_base_url': self.gemilang_base_url,
            'gemilang_search_path': self.gemilang_search_path,
            'juragan_material_base_url': self.juragan_material_base_url,
            'juragan_material_search_path': self.juragan_material_search_path,
            'depobangunan_base_url': self.depobangunan_base_url,
            'depobangunan_search_path': self.depobangunan_search_path,
        }


config = ScraperConfig.from_environment()