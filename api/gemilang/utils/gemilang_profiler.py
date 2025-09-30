import sys
import cProfile
import pstats
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.utils.base_profiler import BaseProfiler
from api.gemilang.factory import create_gemilang_scraper
from api.gemilang.html_parser import GemilangHtmlParser
from api.gemilang.price_cleaner import GemilangPriceCleaner
from api.gemilang.url_builder import GemilangUrlBuilder


class GemilangProfiler(BaseProfiler):
    
    def __init__(self):
        super().__init__('gemilang')
    
    def _setup_vendor_specific(self):
        self.real_scraper = create_gemilang_scraper()
        self.test_keywords = ["cat", "kuas", "paku", "kawat", "semen"]
        self.html_parser = GemilangHtmlParser()
        self.price_cleaner = GemilangPriceCleaner()
        self.url_builder = GemilangUrlBuilder()
    

    
    def _get_fallback_html(self) -> str:
        project_root = Path(__file__).parent.parent.parent.parent
        fixture_path = project_root / 'api' / 'gemilang' / 'tests' / 'gemilang_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html('item-product', 'product-name', 'price', 1500)
    
    def _get_test_prices(self) -> List[str]:
        return [
            "Rp 15.000", "Rp15,000", "Rp 1.500.000", "15000", "Rp. 25.500",
            "Price: Rp 750.000", "Rp 50,000.00", "", None, "Invalid price"
        ]
    
    def _get_test_keywords(self) -> List[str]:
        return [
            "cat tembok", "kuas cat", "paku beton", "kawat ayam",
            "semen portland", "genteng metal", "pipa pvc", "keramik lantai"
        ]
    
    def _create_scraper(self):
        return create_gemilang_scraper()
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_SCRAPER', '3'))
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
    

    

    
    def run_complete_profiling(self):
        self.run_basic_profiling()
        
        if self.ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            return
            
        try:
            # Add Gemilang-specific complete scraper profiling
            self.profile_complete_scraper()
            print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            report_file = self.generate_performance_report()
            print(f"Report saved to: {report_file}")
            
            self.print_performance_summary()
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise


def main():
    profiler = GemilangProfiler()
    profiler.run_complete_profiling()


if __name__ == "__main__":
    main()