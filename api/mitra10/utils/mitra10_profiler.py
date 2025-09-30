import sys
import cProfile
import pstats
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.utils.base_profiler import BaseProfiler
from api.mitra10.factory import create_mitra10_scraper
from api.mitra10.html_parser import Mitra10HtmlParser
from api.mitra10.price_cleaner import Mitra10PriceCleaner
from api.mitra10.url_builder import Mitra10UrlBuilder
from api.playwright_client import PlaywrightHttpClient


class Mitra10Profiler(BaseProfiler):
    
    def __init__(self, output_dir=None):
        super().__init__('mitra10', output_dir)
    
    def _setup_vendor_specific(self):
        self.real_scraper = create_mitra10_scraper()
        self.test_keywords = ["semen", "cat", "paku", "kawat", "keramik"]
        self.html_parser = Mitra10HtmlParser()
        self.price_cleaner = Mitra10PriceCleaner()
        self.url_builder = Mitra10UrlBuilder()
    

    
    def _get_fallback_html(self) -> str:
        project_root = Path(__file__).parent.parent.parent.parent
        fixture_path = project_root / 'api' / 'mitra10' / 'tests' / 'mitra10_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html('MuiGrid-item', 'gtm_mitra10_cta_product', 'price__final', 2500)
    
    def _get_test_prices(self) -> List[str]:
        return [
            "Rp 50.000", "Rp50,000", "Rp 1.250.000", "65000", "Rp. 125.500",
            "Price: Rp 750.000", "Rp 25,000.00", "", None, "Invalid price"
        ]
    
    def _get_test_keywords(self) -> List[str]:
        return [
            "semen portland", "cat tembok", "paku beton", "kawat ayam",
            "keramik lantai", "genteng metal", "pipa pvc", "kabel listrik"
        ]
    
    def _create_scraper(self):
        return create_mitra10_scraper()
    

    

    
    def profile_playwright_client(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_PLAYWRIGHT', '3'))
        print(f"Profiling Playwright client initialization ({iterations} iterations)...")
        
        def playwright_callback(i):
            client = PlaywrightHttpClient(headless=True)
            client.close()
        
        return self._profile_component('playwright_client', iterations, playwright_callback)
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_SCRAPER', '2'))
        
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
                        cleaned_price = scraper.html_parser.price_cleaner.clean_price(str(product.price))
                    
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
            except:
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
    

    
    def generate_performance_report(self) -> str:
        report_file = super().generate_performance_report()
        
        import json
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        report['optimization_recommendations'] = self._generate_recommendations()
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file
    
    def _generate_recommendations(self) -> Dict[str, Any]:
        recommendations = {
            'critical_issues': [],
            'moderate_issues': [],
            'general_optimizations': []
        }
        
        if 'playwright_client' in self.results:
            playwright_time = self.results['playwright_client']['total_time']
            playwright_iterations = self.results['playwright_client']['iterations']
            avg_init_time = playwright_time / playwright_iterations if playwright_iterations > 0 else 0
            
            if avg_init_time > 3:
                recommendations['critical_issues'].append({
                    'issue': 'Playwright initialization bottleneck',
                    'avg_time': avg_init_time,
                    'impact': 'High - blocks scraping operations',
                    'solutions': [
                        'Implement connection pooling',
                        'Keep Browser instances alive between requests',
                        'Consider requests library for static content',
                        'Use persistent browser contexts'
                    ]
                })
            elif avg_init_time > 1:
                recommendations['moderate_issues'].append({
                    'issue': 'Playwright initialization could be improved',
                    'avg_time': avg_init_time,
                    'solutions': ['Browser instance reuse', 'Optimize startup options']
                })
        
        if 'html_parser' in self.results:
            parser_time = self.results['html_parser']['total_time']
            iterations = self.results['html_parser']['iterations']
            avg_parse_time = parser_time / iterations if iterations > 0 else 0
            
            if avg_parse_time > 0.1:
                recommendations['moderate_issues'].append({
                    'issue': 'HTML parsing performance',
                    'avg_time': avg_parse_time,
                    'solutions': [
                        'Switch to lxml parser',
                        'Optimize CSS selectors',
                        'Cache parsed structures',
                        'Use compiled selectors'
                    ]
                })
        
        recommendations['general_optimizations'] = [
            'Implement async/concurrent scraping',
            'Add Redis caching for responses',
            'Use request batching',
            'Implement database connection pooling',
            'Add monitoring and alerting'
        ]
        
        return recommendations
    
    def run_complete_profiling(self):
        self.run_basic_profiling()
        
        if self.ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            return
        
        try:
            # Add Mitra10-specific profiling
            self.profile_playwright_client()
            print(f"Playwright Client: {self.results['playwright_client']['total_time']:.4f}s")
            
            # Optional complete scraper profiling
            proceed = self.ENV.get('PROFILING_AUTO_SCRAPE', 'false').lower() == 'true'
            if not proceed:
                print("\n Real Web Scraping Mode")
                print("This will make actual HTTP requests to Mitra10.com and may take longer.")
                response = input("Proceed with real web scraping? (y/N): ").strip().lower()
                proceed = response == 'y'
            
            if proceed:
                self.profile_complete_scraper()
                print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            report_file = self.generate_performance_report()
            print(f"Report saved to: {report_file}")
            
            self.print_performance_summary()
            self._print_recommendations()
            
            return {
                'report_file': report_file,
                'output_dir': str(self.output_dir),
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
    
    def _print_recommendations(self):
        if not self.results:
            return
        
        print("\nOptimization Recommendations:")
        print("=" * 40)
        
        recommendations = self._generate_recommendations()
        
        if recommendations['critical_issues']:
            print("CRITICAL ISSUES:")
            for issue in recommendations['critical_issues']:
                print(f"  - {issue['issue']} ({issue['avg_time']:.2f}s avg)")
                for solution in issue['solutions'][:2]:  
                    print(f"    * {solution}")
        
        if recommendations['moderate_issues']:
            print("MODERATE ISSUES:")
            for issue in recommendations['moderate_issues']:
                print(f"  - {issue['issue']} ({issue.get('avg_time', 0):.4f}s avg)")
        
        print("GENERAL OPTIMIZATIONS:")
        for opt in recommendations['general_optimizations'][:3]:  
            print(f"  - {opt}")


def main():
    profiler = Mitra10Profiler()
    profiler.run_complete_profiling()


if __name__ == "__main__":
    main()