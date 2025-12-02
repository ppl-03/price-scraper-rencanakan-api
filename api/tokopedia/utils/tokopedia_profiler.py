
import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.utils.base_profiler import BaseProfiler
from api.tokopedia.factory import create_tokopedia_scraper
from api.tokopedia.html_parser import TokopediaHtmlParser
from api.tokopedia.price_cleaner import TokopediaPriceCleaner
from api.tokopedia.url_builder import TokopediaUrlBuilder


class TokopediaProfiler(BaseProfiler):
    
    def __init__(self):
        super().__init__('tokopedia')
    
    def _setup_vendor_specific(self):
        """Setup vendor-specific components and test data"""
        self.real_scraper = create_tokopedia_scraper()
        self.html_parser = TokopediaHtmlParser()
        self.price_cleaner = TokopediaPriceCleaner()
        self.url_builder = TokopediaUrlBuilder()
        self.test_keywords = ["semen", "besi beton", "cat", "paku", "keramik"]
    
    def _get_fallback_html(self) -> str:
        """Get fallback HTML for testing when real data is unavailable"""
        project_root = Path(__file__).parent.parent.parent.parent
        fixture_path = project_root / 'api' / 'tokopedia' / 'tests' / 'tokopedia_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html(
            product_class="css-974ipl",
            product_link_class='a[data-testid="lnkProductContainer"]',
            price_class="css-o5uqv",
            base_price=5000
        )
    
    def _get_test_prices(self) -> List[str]:
        """Return test prices specific to Tokopedia format"""
        return [
            "Rp62.500", "Rp125.000", "Rp1.500.000", "62500", "Rp. 180.000",
            "Price: Rp 950.000", "Rp 75,000.00", "", None, "Invalid price",
            "Rp99.999", "Rp5.000.000", "IDR 250.000", "rp 45.000"
        ]
    
    def _get_test_keywords(self) -> List[str]:
        """Return test keywords for URL building"""
        return [
            "semen portland", "besi beton 10mm", "cat tembok", "paku", 
            "keramik 40x40", "pipa pvc", "genteng metal", "triplek",
            "bata merah", "pasir cor", "kabel listrik", "semen mortar"
        ]
    
    def _create_scraper(self):
        """Create a new scraper instance"""
        return create_tokopedia_scraper()
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        """Profile the complete scraper with real website calls"""
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_SCRAPER', '3'))
        scraper = create_tokopedia_scraper()
        
        print(f"Profiling complete scraper with real website ({iterations} iterations)...")
        
        def scraper_callback(i):
            keyword = self.test_keywords[i % len(self.test_keywords)]
            try:
                result = scraper.scrape_products_with_filters(
                    keyword=keyword,
                    sort_by_price=True,
                    page=0
                )
                print(f"  Scraped {len(result.products)} products for '{keyword}'")
            except Exception as e:
                print(f"  Error scraping '{keyword}': {e}")
        
        result = self._profile_component('complete_scraper', iterations, scraper_callback)
        return result
    
    def profile_scraper_with_filters(self) -> Dict[str, Any]:
        """Profile the scraper with various filter combinations"""
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_FILTERS', '5'))
        scraper = create_tokopedia_scraper()
        
        print(f"Profiling scraper with filters ({iterations} iterations)...")
        
        # Test different filter combinations
        filter_combinations = [
            {'keyword': 'semen', 'min_price': 50000, 'max_price': 100000},
            {'keyword': 'besi', 'min_price': None, 'max_price': 500000},
            {'keyword': 'cat', 'location': 'jakarta'},
            {'keyword': 'keramik', 'min_price': 100000, 'location': 'bandung'},
            {'keyword': 'paku', 'sort_by_price': True, 'page': 1}
        ]
        
        def scraper_callback(i):
            filters = filter_combinations[i % len(filter_combinations)]
            keyword = filters.pop('keyword')
            try:
                result = scraper.scrape_products_with_filters(
                    keyword=keyword,
                    **filters
                )
                print(f"  Scraped {len(result.products)} products with filters: {filters}")
            except Exception as e:
                print(f"  Error with filters: {e}")
        
        result = self._profile_component('scraper_with_filters', iterations, scraper_callback)
        return result
    
    def run_complete_profiling(self):
        """Run complete profiling including the additional tests"""
        if self.ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            print("Profiling is disabled in environment configuration")
            return
            
        try:
            # Run basic profiling from base class
            self.run_basic_profiling()
            
            # Add the complete scraper profiling
            self.profile_complete_scraper()
            print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            # Add the scraper with filters profiling
            self.profile_scraper_with_filters()
            print(f"Scraper with Filters: {self.results['scraper_with_filters']['total_time']:.4f}s")
            
            # Generate report
            report_file = self.generate_performance_report()
            print(f"Report saved to: {report_file}")
            
            # Print summary
            self.print_performance_summary()
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise


def main():
    """Main entry point for running Tokopedia profiler"""
    print("=" * 60)
    print("Tokopedia Scraper Performance Profiler")
    print("=" * 60)
    
    profiler = TokopediaProfiler()
    profiler.run_complete_profiling()
    
    print("\n" + "=" * 60)
    print("Profiling completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
