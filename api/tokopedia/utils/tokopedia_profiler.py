import sys
import time
import json
import cProfile
import pstats
from io import StringIO
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
    
    def _run_scraping_iteration(self, scraper, keyword: str, iteration_num: int, total_iterations: int) -> Dict[str, Any]:
        """Run a single scraping iteration and return results"""
        try:
            iter_start = time.perf_counter()
            result = scraper.scrape_products_with_filters(
                keyword=keyword,
                sort_by_price=True,
                page=0
            )
            iter_end = time.perf_counter()
            
            iter_time = iter_end - iter_start
            iteration_result = {
                'keyword': keyword,
                'products_count': len(result.products),
                'time': iter_time
            }
            
            print(f"  Iteration {iteration_num}/{total_iterations}: '{keyword}' - "
                  f"{len(result.products)} products in {iter_time:.4f}s")
            
            return iteration_result
            
        except Exception as e:
            print(f"  Error on iteration {iteration_num}: {e}")
            return {
                'keyword': keyword,
                'products_count': 0,
                'time': 0,
                'error': str(e)
            }
    
    def _run_scraper_benchmark(self, iterations: int, profiler=None) -> Dict[str, Any]:
        """Run scraper benchmark with optional profiling"""
        scraper = create_tokopedia_scraper()
        results = []
        
        if profiler:
            profiler.enable()
        
        start_time = time.perf_counter()
        
        for i in range(iterations):
            keyword = self.test_keywords[i % len(self.test_keywords)]
            iteration_result = self._run_scraping_iteration(scraper, keyword, i + 1, iterations)
            results.append(iteration_result)
        
        end_time = time.perf_counter()
        
        if profiler:
            profiler.disable()
        
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        benchmark_results = {
            'total_time': total_time,
            'avg_time': avg_time,
            'iterations': iterations,
            'results': results
        }
        
        # Add profiling stats if profiler was used
        if profiler:
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(20)
            benchmark_results['profiling_stats'] = s.getvalue()
        
        return benchmark_results
    
    def run_without_profiling(self, iterations: int = 3) -> Dict[str, Any]:
        """Run scraper without profiling to measure baseline performance"""
        print(f"\n{'='*60}")
        print("Running WITHOUT profiling...")
        print(f"{'='*60}")
        
        return self._run_scraper_benchmark(iterations)
    
    def run_with_profiling(self, iterations: int = 3) -> Dict[str, Any]:
        """Run scraper with profiling enabled to measure overhead"""
        print(f"\n{'='*60}")
        print("Running WITH profiling...")
        print(f"{'='*60}")
        
        profiler = cProfile.Profile()
        return self._run_scraper_benchmark(iterations, profiler=profiler)
    
    def calculate_overhead(self, without: Dict[str, Any], with_prof: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate profiling overhead"""
        if not without or not with_prof:
            return {}
        
        time_overhead = with_prof['total_time'] - without['total_time']
        overhead_percentage = (time_overhead / without['total_time']) * 100
        
        return {
            'time_overhead': time_overhead,
            'overhead_percentage': overhead_percentage,
            'without_profiling_time': without['total_time'],
            'with_profiling_time': with_prof['total_time'],
            'slowdown_factor': with_prof['total_time'] / without['total_time']
        }
    
    def _print_section_header(self, title: str):
        """Print a section header"""
        print(f"\n{title}")
    
    def _print_benchmark_stats(self, title: str, stats: Dict[str, Any]):
        """Print benchmark statistics"""
        self._print_section_header(f"📊 {title}:")
        print(f"  Total Time: {stats['total_time']:.4f}s")
        print(f"  Avg Time/Iteration: {stats['avg_time']:.4f}s")
        print(f"  Iterations: {stats['iterations']}")
    
    def _print_iteration_results(self, title: str, results: List[Dict[str, Any]]):
        """Print detailed iteration results"""
        self._print_section_header(f"  {title}:")
        for i, result in enumerate(results, 1):
            print(f"    {i}. {result['keyword']}: "
                  f"{result['products_count']} products in {result['time']:.4f}s")
    
    def _get_recommendation(self, overhead_percentage: float) -> str:
        """Get performance recommendation based on overhead"""
        if overhead_percentage < 10:
            return "  ✅ Profiling overhead is minimal (<10%). Safe for development."
        elif overhead_percentage < 30:
            return "  ⚠️  Profiling overhead is moderate (10-30%). Use judiciously."
        else:
            return "  ❌ Profiling overhead is significant (>30%). Avoid in production."
    
    def print_comparison_summary(self, without: Dict[str, Any], with_prof: Dict[str, Any], overhead: Dict[str, Any]):
        """Print detailed comparison summary"""
        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON SUMMARY")
        print(f"{'='*60}")
        
        self._print_benchmark_stats("WITHOUT Profiling", without)
        self._print_benchmark_stats("WITH Profiling", with_prof)
        
        self._print_section_header("⚡ Overhead Analysis:")
        print(f"  Time Overhead: {overhead['time_overhead']:.4f}s")
        print(f"  Overhead Percentage: {overhead['overhead_percentage']:.2f}%")
        print(f"  Slowdown Factor: {overhead['slowdown_factor']:.2f}x")
        
        self._print_section_header("📈 Detailed Results:")
        self._print_iteration_results("Without Profiling", without['results'])
        self._print_iteration_results("With Profiling", with_prof['results'])
        
        self._print_section_header("💡 Recommendation:")
        print(self._get_recommendation(overhead['overhead_percentage']))
    
    def _filter_profiling_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove profiling stats from data for cleaner reports"""
        return {k: v for k, v in data.items() if k != 'profiling_stats'}
    
    def save_comparison_report(self, without: Dict[str, Any], with_prof: Dict[str, Any], overhead: Dict[str, Any]):
        """Save comparison report to JSON file"""
        timestamp = int(time.time())
        report_file = self.output_dir / f'profiling_comparison_{timestamp}.json'
        
        report_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'comparison_type': 'profiling_overhead',
            'results': {
                'without_profiling': self._filter_profiling_stats(without),
                'with_profiling': self._filter_profiling_stats(with_prof),
                'overhead_analysis': overhead
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Comparison report saved to: {report_file}")
        return report_file
    
    def _print_summary_stats(self, without: Dict[str, Any], with_prof: Dict[str, Any], overhead: Dict[str, Any]):
        """Print brief comparison summary"""
        print(f"\n{'='*60}")
        print("COMPARISON SUMMARY")
        print(f"{'='*60}")
        print(f"Without Profiling: {without['total_time']:.4f}s (avg: {without['avg_time']:.4f}s)")
        print(f"With Profiling:    {with_prof['total_time']:.4f}s (avg: {with_prof['avg_time']:.4f}s)")
        print(f"Overhead:          {overhead['time_overhead']:.4f}s ({overhead['overhead_percentage']:.2f}%)")
        print(f"Slowdown Factor:   {overhead['slowdown_factor']:.2f}x")
        print(f"\n{self._get_recommendation(overhead['overhead_percentage'])}")
    
    def run_profiling_comparison(self, iterations: int = 3):
        """Run comparison between profiling and non-profiling execution"""
        print("=" * 60)
        print("TOKOPEDIA SCRAPER PROFILING COMPARISON")
        print("=" * 60)
        print(f"\nComparing performance with {iterations} iterations each")
        
        try:
            # Run without profiling
            without = self.run_without_profiling(iterations)
            
            # Small delay between tests
            time.sleep(2)
            
            # Run with profiling
            with_prof = self.run_with_profiling(iterations)
            
            # Calculate overhead
            overhead = self.calculate_overhead(without, with_prof)
            
            # Save report and print summary
            report_file = self.save_comparison_report(without, with_prof, overhead)
            self._print_summary_stats(without, with_prof, overhead)
            
            print(f"\n📄 Full report saved to: {report_file}")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"\n❌ Comparison failed: {e}")
            raise


def main():
    """Main entry point for running Tokopedia profiler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tokopedia Scraper Performance Profiler and Comparison')
    parser.add_argument(
        '--iterations',
        type=int,
        default=3,
        help='Number of iterations for comparison (default: 3)'
    )
    
    args = parser.parse_args()
    
    profiler = TokopediaProfiler()
    profiler.run_profiling_comparison(iterations=args.iterations)


if __name__ == "__main__":
    main()
