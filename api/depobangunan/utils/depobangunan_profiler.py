import sys
import cProfile
import pstats
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.utils.base_profiler import BaseProfiler
from api.depobangunan.factory import create_depo_scraper
from api.depobangunan.html_parser import DepoHtmlParser
from api.depobangunan.price_cleaner import DepoPriceCleaner
from api.depobangunan.url_builder import DepoUrlBuilder


class DepoBangunanProfiler(BaseProfiler):
    
    def __init__(self):
        super().__init__('depobangunan')
    
    def _setup_vendor_specific(self):
        self.real_scraper = create_depo_scraper()
        self.test_keywords = ["cat", "semen", "paku", "genteng", "keramik"]
        self.html_parser = DepoHtmlParser()
        self.price_cleaner = DepoPriceCleaner()
        self.url_builder = DepoUrlBuilder()
    
    def _get_fallback_html(self) -> str:
        project_root = Path(__file__).parent.parent.parent.parent
        fixture_path = project_root / 'api' / 'depobangunan' / 'tests' / 'depo_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html('item product product-item', 'product-item-link', 'price', 3600)
    
    def _get_test_prices(self) -> List[str]:
        return [
            "Rp 3.600", "Rp 125.000", "Rp 1.500.000", "3600", "Rp. 25.500",
            "Price: Rp 750.000", "Rp 50,000", "", None, "Invalid price"
        ]
    
    def _get_test_keywords(self) -> List[str]:
        return [
            "cat tembok", "semen portland", "paku beton", "genteng metal",
            "keramik lantai", "bata merah", "pasir", "besi beton"
        ]
    
    def _create_scraper(self):
        return create_depo_scraper()
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_SCRAPER', '3'))
        scraper = create_depo_scraper()
        
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
            # Add Depobangunan-specific complete scraper profiling
            self.profile_complete_scraper()
            print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            report_file = self.generate_performance_report()
            print(f"Report saved to: {report_file}")
            
            self.print_performance_summary()
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise


def main():
    profiler = DepoBangunanProfiler()
    profiler.run_complete_profiling()


if __name__ == "__main__":
    main()
