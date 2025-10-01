import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from api.utils.base_profiler import BaseProfiler
from api.juragan_material.factory import create_juraganmaterial_scraper
from api.juragan_material.html_parser import JuraganMaterialHtmlParser
from api.juragan_material.price_cleaner import JuraganMaterialPriceCleaner
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder


class JuraganMaterialProfiler(BaseProfiler):
    
    def __init__(self):
        super().__init__('juraganmaterial')
    
    def _setup_vendor_specific(self):
        """Setup vendor-specific components and test data"""
        self.real_scraper = create_juraganmaterial_scraper()
        self.html_parser = JuraganMaterialHtmlParser()
        self.price_cleaner = JuraganMaterialPriceCleaner()
        self.url_builder = JuraganMaterialUrlBuilder()
        self.test_keywords = ["semen", "besi", "pasir", "batu bata", "genteng"]
    
    def _get_fallback_html(self) -> str:
        """Get fallback HTML for testing when real data is unavailable"""
        project_root = Path(__file__).parent.parent.parent.parent
        fixture_path = project_root / 'api' / 'juragan_material' / 'tests' / 'juraganmaterial_mock_results.html'
        if fixture_path.exists():
            return fixture_path.read_text(encoding='utf-8')
        return self._create_mock_html(
            product_class="product-card",
            product_link_class="product-link",
            price_class="price",
            base_price=2500
        )
    
    def _get_test_prices(self) -> List[str]:
        """Return test prices specific to Juragan Material format"""
        return [
            "Rp 60.500", "Rp60,500", "Rp 1.234.567", "60500", "Rp. 120.000",
            "Price: Rp 750.000", "Rp 50,000.00", "", None, "Invalid price"
        ]
    
    def _get_test_keywords(self) -> List[str]:
        """Return test keywords for URL building"""
        return [
            "semen portland", "besi beton", "pasir cor", "batu bata merah",
            "genteng metal", "pipa pvc", "keramik lantai", "cat tembok"
        ]
    
    def _create_scraper(self):
        """Create a new scraper instance"""
        return create_juraganmaterial_scraper()
    
    def profile_complete_scraper(self) -> Dict[str, Any]:
        """Profile the complete scraper with real website calls"""
        iterations = int(self.ENV.get('PROFILING_ITERATIONS_SCRAPER', '3'))
        scraper = create_juraganmaterial_scraper()
        
        print(f"Profiling complete scraper with real website ({iterations} iterations)...")
        
        def scraper_callback(i):
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
        
        result = self._profile_component('complete_scraper', iterations, scraper_callback)
        return result
    
    def run_complete_profiling(self):
        """Run complete profiling including the additional complete_scraper test"""
        if self.ENV.get('PROFILING_ENABLED', 'true').lower() != 'true':
            print("Profiling is disabled in environment configuration")
            return
            
        try:
            # Run basic profiling from base class
            self.run_basic_profiling()
            
            # Add the complete scraper profiling
            self.profile_complete_scraper()
            print(f"Complete Scraper: {self.results['complete_scraper']['total_time']:.4f}s")
            
            # Generate report
            report_file = self.generate_performance_report()
            print(f"Report saved to: {report_file}")
            
            # Print summary
            self.print_performance_summary()
            
        except Exception as e:
            print(f"Profiling failed: {e}")
            raise


def main():
    profiler = JuraganMaterialProfiler()
    profiler.run_complete_profiling()


if __name__ == "__main__":
    main()