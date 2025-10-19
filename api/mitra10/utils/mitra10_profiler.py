from api.mitra10.factory import create_mitra10_scraper
from api.mitra10.html_parser import Mitra10HtmlParser
from api.mitra10.price_cleaner import Mitra10PriceCleaner
from api.mitra10.url_builder import Mitra10UrlBuilder
from api.playwright_client import PlaywrightHttpClient
import cProfile
import pstats
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

project_root = Path(__file__).parent.parent.parent.parent
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


class Mitra10Profiler:
    
    def __init__(self, output_dir=None):
        self.results = {}
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            output_dir_name = ENV.get('PROFILING_OUTPUT_DIR', 'mitra10_profiling')
            self.output_dir = project_root / output_dir_name
        self.output_dir.mkdir(exist_ok=True)
        self.real_scraper = create_mitra10_scraper()
        self.test_keywords = ["semen", "cat", "paku", "kawat", "keramik"]
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
        fixture_path = project_root / 'api' / 'mitra10' / 'tests' / 'mitra10_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html()
    
    def _create_mock_html(self) -> str:
        num_products = int(ENV.get('MOCK_HTML_PRODUCTS', '50'))
        products = []
        for i in range(num_products):
            product = f'''
            <div class="MuiGrid-item">
                <a class="gtm_mitra10_cta_product" href="/product/mitra10-product-{i}">
                    <p>Mitra10 Product {i}</p>
                </a>
                <span class="price__final">Rp {(i + 1) * 2500:,}</span>
            </div>
            '''
            products.append(product)
        
        return f'<html><body><div class="products-container">{"".join(products)}</div></body></html>'
    
    def profile_html_parser(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_HTML', '5'))
        parser = Mitra10HtmlParser()
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
        cleaner = Mitra10PriceCleaner()
        test_prices = [
            "Rp 50.000", "Rp50,000", "Rp 1.250.000", "65000", "Rp. 125.500",
            "Price: Rp 750.000", "Rp 25,000.00", "", None, "Invalid price"
        ]
        
        profiler = cProfile.Profile()
        
        profiler.enable()
        for _ in range(iterations):
            for price in test_prices:
                try:
                    cleaned = cleaner.clean_price(price)
                    cleaner.is_valid_price(cleaned)
                except (ValueError, TypeError, AttributeError):
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
        builder = Mitra10UrlBuilder()
        test_keywords = [
            "semen portland", "cat tembok", "paku beton", "kawat ayam",
            "keramik lantai", "genteng metal", "pipa pvc", "kabel listrik"
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
    
    def profile_playwright_client(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_PLAYWRIGHT', '3'))
        profiler = cProfile.Profile()
        
        print(f"Profiling Playwright client initialization ({iterations} iterations)...")
        
        profiler.enable()
        for _ in range(iterations):
            try:
                client = PlaywrightHttpClient(headless=True)
                client.close()
            except Exception as e:
                print(f"  Playwright error: {e}")
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        stats_file = self.output_dir / "playwright_client_profile.txt"
        with open(stats_file, 'w') as f:
            old_stdout = sys.stdout
            sys.stdout = f
            stats.print_stats()
            sys.stdout = old_stdout
        
        result = {
            'component': 'playwright_client',
            'iterations': iterations,
            'stats_file': str(stats_file),
            'total_calls': stats.total_calls,
            'total_time': stats.total_tt
        }
        
        self.results['playwright_client'] = result
        return result
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        iterations = int(ENV.get('PROFILING_ITERATIONS_SCRAPER', '2'))
        
        print(f"Profiling complete scraper with REAL WEB SCRAPING ({iterations} iterations)...")
        print("This will make actual HTTP requests to Mitra10.com")
        profiler = cProfile.Profile()
        
        profiler.enable()
        try:
            scraper = create_mitra10_scraper()
            
            for i in range(iterations):
                keyword = self.test_keywords[i % len(self.test_keywords)]
                try:
                    print(f"Scraping real data for '{keyword}'...")
                    
                    url = scraper.url_builder.build_search_url(keyword, True, 0)                    
                    html_content = scraper.http_client.get(url)
                    products = scraper.html_parser.parse_products(html_content)
                    
                    for product in products[:5]:  
                        scraper.html_parser.price_cleaner.clean_price(str(product.price))
                    
                    products_found = len(products)
                    html_size = len(html_content)
                    print(f"Found {products_found} products for '{keyword}' (HTML: {html_size:,} chars)")
                    
                    if products:
                        sample = products[0]
                        print(f"Sample: {sample.name[:50]}... - Rp {sample.price:,}")
                        
                except Exception as e:
                    print(f"Error scraping '{keyword}': {e}")
                    try:
                        mock_html = self._get_fallback_html()
                        products = scraper.html_parser.parse_products(mock_html)
                        print(f"Fallback: {len(products)} mock products for '{keyword}'")
                    except Exception as fallback_error:
                        print(f"Fallback failed: {fallback_error}")
                    
        except Exception as e:
            print(f"Failed to initialize scraper: {e}")
        finally:
            try:
                if 'scraper' in locals():
                    scraper.http_client.close()
            except (AttributeError, RuntimeError, ConnectionError) as e:
                pass
        
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
                scraper = create_mitra10_scraper()
                if hasattr(scraper.http_client, 'close'):
                    scraper.http_client.close()
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
        
        report_file = self.output_dir / f"mitra10_performance_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_file)
    
    def run_complete_profiling(self):
        if ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            print("Profiling is disabled in environment configuration")
            return
        
        try:
            print("Starting Mitra10 profiling...")
            
            self.profile_url_builder()
            print(f"URL Builder: {self.results['url_builder']['total_time']:.4f}s")
            
            self.profile_price_cleaner()
            print(f"Price Cleaner: {self.results['price_cleaner']['total_time']:.4f}s")
            
            self.profile_html_parser()
            print(f"HTML Parser: {self.results['html_parser']['total_time']:.4f}s")
            
            self.profile_factory()
            print(f"Factory: {self.results['factory']['total_time']:.4f}s")
            
            self.profile_playwright_client()
            print(f"Playwright Client: {self.results['playwright_client']['total_time']:.4f}s")
            
            proceed = ENV.get('PROFILING_AUTO_SCRAPE', 'false').lower() == 'true'
            if not proceed:
                print("\nReal Web Scraping Mode")
                print("This will make actual HTTP requests to Mitra10.com and may take longer.")
                response = input("Proceed with real web scraping? (y/N): ").strip().lower()
                proceed = response == 'y'
            
            if proceed:
                self.profile_complete_scraper()
                print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            report_file = self.generate_performance_report()
            
            print("\nMitra10 Profiling Complete")
            print(f"Report saved to: {report_file}")
            print(f"Profile files in: {self.output_dir}")
            
            print("\nPerformance Summary:")
            for component, data in self.results.items():
                calls_per_sec = data['total_calls'] / data['total_time'] if data['total_time'] > 0 else 0
                print(f"  {component}: {data['total_time']:.4f}s ({data['total_calls']:,} calls, {calls_per_sec:.0f} calls/sec)")
            
            return {
                'report_file': report_file,
                'output_dir': self.output_dir,
                'results': [
                    {
                        'component': component,
                        'average_time': data['total_time'],
                        'total_calls': data['total_calls'],
                        'calls_per_second': data['total_calls'] / data['total_time'] if data['total_time'] > 0 else 0
                    }
                    for component, data in self.results.items()
                ]
            }
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise
    
def main():
    profiler = Mitra10Profiler()
    profiler.run_complete_profiling()


if __name__ == "__main__":
    main()