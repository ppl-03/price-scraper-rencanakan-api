import cProfile
import pstats
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def load_env():
    env_file = project_root / '.env'
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

ENV = load_env()

from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.html_parser import GemilangHtmlParser
from api.gemilang.price_cleaner import GemilangPriceCleaner
from api.gemilang.url_builder import GemilangUrlBuilder


class GemilangProfiler:
    
    def __init__(self):
        self.results = {}
        output_dir_name = ENV.get('PROFILING_OUTPUT_DIR', 'gemilang_profiling')
        self.output_dir = project_root / output_dir_name
        self.output_dir.mkdir(exist_ok=True)
        self.real_scraper = create_gemilang_scraper()
        self.test_keywords = ["cat", "kuas", "paku", "kawat", "semen"]
        self.real_html_cache = {}
    
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
    
    def _get_fallback_html(self) -> str:
        fixture_path = project_root / 'api' / 'gemilang' / 'tests' / 'gemilang_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html()
    
    def _create_mock_html(self) -> str:
        num_products = int(ENV.get('MOCK_HTML_PRODUCTS', '50'))
        products = []
        for i in range(num_products):
            product = f'''
            <div class="item-product">
                <a href="/pusat/product-{i}">
                    <p class="product-name">Gemilang Product {i}</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">Rp {(i + 1) * 1500:,}</p>
                </div>
            </div>
            '''
            products.append(product)
        
        return f'<html><body><div class="products-container">{"".join(products)}</div></body></html>'
    
    def profile_html_parser(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_HTML', '5'))
        parser = GemilangHtmlParser()
        profiler = cProfile.Profile()
        
        print(f"Profiling HTML parser with real data ({iterations} iterations)...")
        real_html = self._fetch_real_html(self.test_keywords[0])
        
        profiler.enable()
        for _ in range(iterations):
            try:
                parser.parse_products(real_html)
            except Exception as e:
                print(f"Parse error: {e}")
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / "html_parser_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': 'html_parser',
            'iterations': iterations,
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results['html_parser'] = result
        return result
    
    def profile_price_cleaner(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_PRICE', '1000'))
        cleaner = GemilangPriceCleaner()
        test_prices = [
            "Rp 15.000", "Rp15,000", "Rp 1.500.000", "15000", "Rp. 25.500",
            "Price: Rp 750.000", "Rp 50,000.00", "", None, "Invalid price"
        ]
        
        profiler = cProfile.Profile()
        
        profiler.enable()
        for _ in range(iterations):
            for price in test_prices:
                try:
                    cleaner.clean_price(price)
                except (TypeError, ValueError, AttributeError):
                    pass
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / "price_cleaner_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': 'price_cleaner',
            'iterations': iterations,
            'test_prices_count': len(test_prices),
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results['price_cleaner'] = result
        return result
    
    def profile_url_builder(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_URL', '500'))
        builder = GemilangUrlBuilder()
        test_keywords = [
            "cat tembok", "kuas cat", "paku beton", "kawat ayam",
            "semen portland", "genteng metal", "pipa pvc", "keramik lantai"
        ]
        
        profiler = cProfile.Profile()
        
        profiler.enable()
        for i in range(iterations):
            keyword = test_keywords[i % len(test_keywords)]
            try:
                builder.build_search_url(keyword, True, i % 5)
            except Exception:
                pass
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / "url_builder_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': 'url_builder',
            'iterations': iterations,
            'keywords_count': len(test_keywords),
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results['url_builder'] = result
        return result
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_SCRAPER', '3'))
        scraper = create_gemilang_scraper()
        
        print(f"Profiling complete scraper with real website ({iterations} iterations)...")
        profiler = cProfile.Profile()
        
        profiler.enable()
        for i in range(iterations):
            keyword = self.test_keywords[i % len(self.test_keywords)]
            try:
                result = scraper.scrape_products(
                    keyword=keyword,
                    sort_by_price=True,
                    page=0
                )
                print(f"  Scraped {len(result)} products for '{keyword}'")
            except Exception as e:
                print(f"  Error scraping '{keyword}': {e}")
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / "complete_scraper_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': 'complete_scraper',
            'iterations': iterations,
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results['complete_scraper'] = result
        return result
    
    def profile_factory(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_FACTORY', '100'))
        profiler = cProfile.Profile()
        
        profiler.enable()
        for _ in range(iterations):
            try:
                create_gemilang_scraper()
            except Exception:
                pass
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / "factory_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': 'factory',
            'iterations': iterations,
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results['factory'] = result
        return result
    
    def generate_performance_report(self) -> str:
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'profiling_results': self.results,
            'environment_config': {k: v for k, v in ENV.items() if k.startswith('PROFILING_')}
        }
        
        report_file = self.output_dir / f"gemilang_performance_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_file)
    
    def run_complete_profiling(self):
        if ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            print("Profiling is disabled in environment configuration")
            return
            
        try:
            print("Starting Gemilang profiling...")
            
            self.profile_html_parser()
            print(f"HTML Parser: {self.results['html_parser']['total_time']:.4f}s")
            
            self.profile_price_cleaner()
            print(f"Price Cleaner: {self.results['price_cleaner']['total_time']:.4f}s")
            
            self.profile_url_builder()
            print(f"URL Builder: {self.results['url_builder']['total_time']:.4f}s")
            
            self.profile_factory()
            print(f"Factory: {self.results['factory']['total_time']:.4f}s")
            
            self.profile_complete_scraper()
            print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            report_file = self.generate_performance_report()
            
            print("\nGemilang Profiling Complete")
            print(f"Report saved to: {report_file}")
            print(f"Profile files in: {self.output_dir}")
            
            print("\nPerformance Summary:")
            for component, data in self.results.items():
                calls_per_sec = data['total_calls'] / data['total_time'] if data['total_time'] > 0 else 0
                print(f"  {component}: {data['total_time']:.4f}s ({data['total_calls']:,} calls, {calls_per_sec:.0f} calls/sec)")
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise


def main():
    profiler = GemilangProfiler()
    profiler.run_complete_profiling()


if __name__ == "__main__":
    main()