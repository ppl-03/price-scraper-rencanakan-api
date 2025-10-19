import cProfile
import pstats
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


def load_env():
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / '.env'
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars


class BaseProfiler(ABC):
    
    def __init__(self, vendor_name: str, output_dir: Optional[str] = None):
        self.vendor_name = vendor_name
        self.results = {}
        self.ENV = load_env()
        
        project_root = Path(__file__).parent.parent.parent
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            output_dir_name = self.ENV.get('PROFILING_OUTPUT_DIR', f'{vendor_name}_profiling')
            self.output_dir = project_root / output_dir_name
        self.output_dir.mkdir(exist_ok=True)
        
        self.real_html_cache = {}
        self._setup_vendor_specific()
    
    @abstractmethod
    def _setup_vendor_specific(self):
        pass
    
    @abstractmethod
    def _get_fallback_html(self) -> str:
        pass
    
    def _fetch_real_html(self, keyword: str) -> str:
        if keyword in self.real_html_cache:
            return self.real_html_cache[keyword]
        
        try:
            url = self.real_scraper.url_builder.build_search_url(keyword, True, 0)
            html_content = self.real_scraper.http_client.get(url)
            self.real_html_cache[keyword] = html_content
            return html_content
        except Exception as e:
            print(f"Failed to fetch real data for {keyword}: {e}")
            return self._get_fallback_html()
    
    def _create_mock_html(self, product_class: str, product_link_class: str, 
                         price_class: str, base_price: int = 1500) -> str:
        num_products = int(self.ENV.get('MOCK_HTML_PRODUCTS', '50'))
        products = []
        for i in range(num_products):
            product = f'''
            <div class="{product_class}">
                <a class="{product_link_class}" href="/product/{self.vendor_name.lower()}-product-{i}">
                    <p>{self.vendor_name.title()} Product {i}</p>
                </a>
                <span class="{price_class}">Rp {(i + 1) * base_price:,}</span>
            </div>
            '''
            products.append(product)
        
        return f'<html><body><div class="products-container">{"".join(products)}</div></body></html>'
    
    def _profile_component(self, component_name: str, iterations: int, 
                          callback, *args, **kwargs) -> Dict[str, Any]:
        profiler = cProfile.Profile()
        
        profiler.enable()
        for i in range(iterations):
            try:
                callback(i, *args, **kwargs)
            except Exception as e:
                if self.ENV.get('PROFILING_DEBUG', 'false').lower() == 'true':
                    print(f"Error in {component_name} iteration {i}: {e}")
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / f"{component_name}_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': component_name,
            'iterations': iterations,
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results[component_name] = result
        return result
    
    def profile_html_parser(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_HTML', '5'))
        print(f"Profiling HTML parser with real data ({iterations} iterations)...")
        real_html = self._fetch_real_html(self.test_keywords[0])
        
        def parse_callback(i):
            self.html_parser.parse_products(real_html)
        
        return self._profile_component('html_parser', iterations, parse_callback)
    
    def profile_price_cleaner(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_PRICE', '1000'))
        test_prices = self._get_test_prices()
        
        def price_clean_callback(i):
            for price in test_prices:
                try:
                    cleaned = self.price_cleaner.clean_price(price)
                    if hasattr(self.price_cleaner, 'is_valid_price'):
                        self.price_cleaner.is_valid_price(cleaned)
                except (TypeError, ValueError, AttributeError):
                    pass
        
        result = self._profile_component('price_cleaner', iterations, price_clean_callback)
        result['test_prices_count'] = len(test_prices)
        return result
    
    def profile_url_builder(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_URL', '500'))
        test_keywords = self._get_test_keywords()
        
        def url_build_callback(i):
            keyword = test_keywords[i % len(test_keywords)]
            self.url_builder.build_search_url(keyword, True, i % 5)
        
        result = self._profile_component('url_builder', iterations, url_build_callback)
        result['keywords_count'] = len(test_keywords)
        return result
    
    def profile_factory(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_FACTORY', '100'))
        
        def factory_callback(i):
            scraper = self._create_scraper()
            if hasattr(scraper, 'http_client') and hasattr(scraper.http_client, 'close'):
                scraper.http_client.close()
        
        return self._profile_component('factory', iterations, factory_callback)
    
    @abstractmethod
    def _get_test_prices(self) -> List[str]:
        pass
    
    @abstractmethod
    def _get_test_keywords(self) -> List[str]:
        pass
    
    @abstractmethod
    def _create_scraper(self):
        pass
    
    def generate_performance_report(self) -> str:
        report = {
            'vendor': self.vendor_name,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'profiling_results': self.results,
            'environment_config': {k: v for k, v in self.ENV.items() if k.startswith('PROFILING_')}
        }
        
        report_file = self.output_dir / f"{self.vendor_name}_performance_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_file)
    
    def print_performance_summary(self):
        print(f"\n{self.vendor_name.title()} Profiling Complete")
        print(f"Profile files in: {self.output_dir}")
        
        print("\nPerformance Summary:")
        for component, data in self.results.items():
            calls_per_sec = data['total_calls'] / data['total_time'] if data['total_time'] > 0 else 0
            print(f"  {component}: {data['total_time']:.4f}s ({data['total_calls']:,} calls, {calls_per_sec:.0f} calls/sec)")
    
    def run_basic_profiling(self):
        if self.ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            print("Profiling is disabled in environment configuration")
            return
        
        try:
            print(f"Starting {self.vendor_name.title()} profiling...")
            
            self.profile_html_parser()
            print(f"HTML Parser: {self.results['html_parser']['total_time']:.4f}s")
            
            self.profile_price_cleaner()
            print(f"Price Cleaner: {self.results['price_cleaner']['total_time']:.4f}s")
            
            self.profile_url_builder()
            print(f"URL Builder: {self.results['url_builder']['total_time']:.4f}s")
            
            self.profile_factory()
            print(f"Factory: {self.results['factory']['total_time']:.4f}s")
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise