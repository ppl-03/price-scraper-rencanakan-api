import unittest
from unittest.mock import patch
from django.test import TestCase
from urllib.parse import urlparse, parse_qs

from api.tokopedia.url_builder import TokopediaUrlBuilder
from api.interfaces import UrlBuilderError


class TestTokopediaUrlBuilder(TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.url_builder = TokopediaUrlBuilder()
        self.base_url = "https://www.tokopedia.com"
        self.search_path = "/p/pertukangan/material-bangunan"
    
    # Initialization Tests
    
    def test_initialization_with_defaults(self):
        """Test URL builder initialization with default values"""
        builder = TokopediaUrlBuilder()
        self.assertEqual(builder.base_url, "https://www.tokopedia.com")
        self.assertEqual(builder.search_path, "/p/pertukangan/material-bangunan")
    
    def test_initialization_with_custom_values(self):
        """Test URL builder initialization with custom values"""
        custom_base = "https://custom.tokopedia.com"
        custom_path = "/custom/path"
        builder = TokopediaUrlBuilder(base_url=custom_base, search_path=custom_path)
        self.assertEqual(builder.base_url, custom_base)
        self.assertEqual(builder.search_path, custom_path)
    
    def test_initialization_with_none_values(self):
        """Test URL builder initialization with None values uses defaults"""
        builder = TokopediaUrlBuilder(base_url=None, search_path=None)
        self.assertEqual(builder.base_url, "https://www.tokopedia.com")
        self.assertEqual(builder.search_path, "/p/pertukangan/material-bangunan")
    
    # Basic URL Building Tests (inherited from BaseUrlBuilder)
    
    def test_basic_search_url_building(self):
        """Test basic URL building for Tokopedia search"""
        keyword = "semen"
        url = self.url_builder.build_search_url(keyword, sort_by_price=True)
        
        expected_base = f"{self.base_url}{self.search_path}"
        self.assertTrue(url.startswith(expected_base))
        self.assertIn('q=semen', url)
        self.assertIn('ob=3', url)  # Tokopedia-specific sort by lowest price
    
    def test_search_url_without_price_sorting(self):
        """Test URL building without price sorting"""
        keyword = "bata merah"
        url = self.url_builder.build_search_url(keyword, sort_by_price=False)
        
        self.assertIn('q=bata+merah', url)
        self.assertNotIn('ob=3', url)
    
    def test_search_url_with_pagination(self):
        """Test URL building with pagination"""
        keyword = "semen"
        url = self.url_builder.build_search_url(keyword, page=2)
        
        self.assertIn('q=semen', url)
        self.assertIn('page=3', url)  # Tokopedia uses 1-based pagination (page 2 becomes page=3)
    
    def test_search_url_with_zero_page(self):
        """Test URL building with page 0 (first page)"""
        keyword = "semen"
        url = self.url_builder.build_search_url(keyword, page=0)
        
        self.assertIn('q=semen', url)
        self.assertNotIn('page=', url)  # Page 0 should not add page parameter
    
    # Parameter Building Tests
    
    def test_build_params_method(self):
        """Test the _build_params method directly"""
        params = self.url_builder._build_params("semen", True, 0)
        expected = {'q': 'semen', 'ob': '3'}
        self.assertEqual(params, expected)
        
        params_no_sort = self.url_builder._build_params("semen", False, 1)
        expected_no_sort = {'q': 'semen', 'page': 2}
        self.assertEqual(params_no_sort, expected_no_sort)
    
    def test_build_params_with_special_characters(self):
        """Test parameter building with special characters in keyword"""
        params = self.url_builder._build_params("semen & bata", True, 0)
        expected = {'q': 'semen & bata', 'ob': '3'}
        self.assertEqual(params, expected)
    
    def test_build_params_with_unicode(self):
        """Test parameter building with Unicode characters"""
        params = self.url_builder._build_params("semen 40kg", True, 0)
        expected = {'q': 'semen 40kg', 'ob': '3'}
        self.assertEqual(params, expected)
    
    # Advanced URL Building with Filters Tests
    
    def test_advanced_url_with_price_filters(self):
        """Test URL building with price range filters"""
        keyword = "semen"
        url = self.url_builder.build_search_url_with_filters(
            keyword=keyword,
            sort_by_price=True,
            min_price=50000,
            max_price=100000
        )
        
        self.assertIn('q=semen', url)
        self.assertIn('ob=3', url)
        self.assertIn('pmin=50000', url)
        self.assertIn('pmax=100000', url)
    
    def test_advanced_url_with_minimum_price_only(self):
        """Test URL building with only minimum price filter"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="bata merah",
            min_price=25000
        )
        
        self.assertIn('q=bata+merah', url)
        self.assertIn('pmin=25000', url)
        self.assertNotIn('pmax=', url)
    
    def test_advanced_url_with_maximum_price_only(self):
        """Test URL building with only maximum price filter"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="genteng",
            max_price=75000
        )
        
        self.assertIn('q=genteng', url)
        self.assertIn('pmax=75000', url)
        self.assertNotIn('pmin=', url)
    
    def test_advanced_url_with_single_location_id(self):
        """Test URL building with single location ID"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="bata merah",
            location_ids=176  # Jakarta
        )
        
        self.assertIn('q=bata+merah', url)
        self.assertIn('fcity=176', url)
    
    def test_advanced_url_with_multiple_location_ids(self):
        """Test URL building with multiple location IDs"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            location_ids=[174, 175, 176]  # Multiple Jakarta areas
        )
        
        self.assertIn('q=semen', url)
        self.assertIn('fcity=174%2C175%2C176', url)  # URL encoded comma-separated list
    
    def test_advanced_url_with_empty_location_list(self):
        """Test URL building with empty location list"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            location_ids=[]
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('fcity=', url)  # Empty list should not add fcity parameter
    
    def test_advanced_url_with_all_filters(self):
        """Test URL building with all filters combined"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen portland",
            sort_by_price=True,
            page=1,
            min_price=50000,
            max_price=100000,
            location_ids=[174, 175, 176]
        )
        
        # Parse URL to check all parameters
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        self.assertIn('semen+portland', url)
        self.assertEqual(params['q'], ['semen portland'])
        self.assertEqual(params['ob'], ['3'])
        self.assertEqual(params['page'], ['2'])  # page 1 becomes page=2
        self.assertEqual(params['pmin'], ['50000'])
        self.assertEqual(params['pmax'], ['100000'])
        self.assertEqual(params['fcity'], ['174,175,176'])
    
    def test_advanced_url_with_pagination(self):
        """Test URL building with filters and pagination"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="genteng",
            page=3,
            min_price=30000
        )
        
        self.assertIn('q=genteng', url)
        self.assertIn('page=4', url)  # page 3 becomes page=4
        self.assertIn('pmin=30000', url)
    
    # Validation and Error Handling Tests
    
    def test_build_search_url_with_filters_empty_keyword(self):
        """Test error handling for empty keyword"""
        with self.assertRaises(ValueError) as context:
            self.url_builder.build_search_url_with_filters("")
        
        self.assertIn("Keyword cannot be empty", str(context.exception))
    
    def test_build_search_url_with_filters_whitespace_keyword(self):
        """Test error handling for whitespace-only keyword"""
        with self.assertRaises(ValueError) as context:
            self.url_builder.build_search_url_with_filters("   ")
        
        self.assertIn("Keyword cannot be empty", str(context.exception))
    
    def test_build_search_url_with_filters_none_keyword(self):
        """Test error handling for None keyword"""
        with self.assertRaises(ValueError) as context:
            self.url_builder.build_search_url_with_filters(None)
        
        self.assertIn("Keyword cannot be empty", str(context.exception))
    
    def test_build_search_url_with_filters_negative_page(self):
        """Test error handling for negative page number"""
        with self.assertRaises(ValueError) as context:
            self.url_builder.build_search_url_with_filters("semen", page=-1)
        
        self.assertIn("Page number cannot be negative", str(context.exception))
    
    def test_build_search_url_with_filters_zero_min_price(self):
        """Test that zero minimum price is ignored"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            min_price=0
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('pmin=', url)  # Zero price should not be added
    
    def test_build_search_url_with_filters_negative_min_price(self):
        """Test that negative minimum price is ignored"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            min_price=-1000
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('pmin=', url)  # Negative price should not be added
    
    def test_build_search_url_with_filters_zero_max_price(self):
        """Test that zero maximum price is ignored"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            max_price=0
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('pmax=', url)  # Zero price should not be added
    
    def test_build_search_url_with_filters_negative_max_price(self):
        """Test that negative maximum price is ignored"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            max_price=-500
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('pmax=', url)  # Negative price should not be added
    
    def test_build_search_url_with_filters_zero_location_id(self):
        """Test that zero location ID is ignored"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            location_ids=0
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('fcity=', url)  # Zero location ID should not be added
    
    def test_build_search_url_with_filters_negative_location_id(self):
        """Test that negative location ID is ignored"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            location_ids=-1
        )
        
        self.assertIn('q=semen', url)
        self.assertNotIn('fcity=', url)  # Negative location ID should not be added
    
    def test_build_search_url_with_filters_none_parameters(self):
        """Test URL building with None filter parameters"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen",
            sort_by_price=True,
            page=0,
            min_price=None,
            max_price=None,
            location_ids=None
        )
        
        self.assertIn('q=semen', url)
        self.assertIn('ob=3', url)
        self.assertNotIn('pmin=', url)
        self.assertNotIn('pmax=', url)
        self.assertNotIn('fcity=', url)
        self.assertNotIn('page=', url)
    
    # URL Structure and Encoding Tests
    
    def test_url_structure_and_encoding(self):
        """Test that URL structure is correct and properly encoded"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen & bata merah",
            min_price=50000
        )
        
        parsed = urlparse(url)
        
        # Check URL structure
        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.netloc, 'www.tokopedia.com')
        self.assertEqual(parsed.path, '/p/pertukangan/material-bangunan')
        
        # Check parameter encoding
        params = parse_qs(parsed.query)
        self.assertEqual(params['q'], ['semen & bata merah'])
        self.assertEqual(params['pmin'], ['50000'])
    
    def test_keyword_trimming(self):
        """Test that keywords are properly trimmed"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="  semen portland  "
        )
        
        # Should trim whitespace from keyword
        self.assertIn('q=semen+portland', url)
        self.assertNotIn('q=++semen+portland++', url)
    
    def test_url_encoding_special_characters(self):
        """Test URL encoding of special characters"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen 40kg/50kg"
        )
        
        # Forward slash should be encoded
        self.assertIn('semen+40kg%2F50kg', url)
    
    # Integration Tests
    
    def test_build_search_url_compatibility(self):
        """Test that build_search_url_with_filters is compatible with build_search_url"""
        keyword = "semen"
        sort_by_price = True
        page = 1
        
        # Build URL using both methods
        basic_url = self.url_builder.build_search_url(keyword, sort_by_price, page)
        advanced_url = self.url_builder.build_search_url_with_filters(
            keyword=keyword,
            sort_by_price=sort_by_price,
            page=page
        )
        
        # Both should produce the same URL
        self.assertEqual(basic_url, advanced_url)
    
    def test_real_world_scenario(self):
        """Test a real-world scenario with realistic parameters"""
        url = self.url_builder.build_search_url_with_filters(
            keyword="semen gresik 40kg",
            sort_by_price=True,
            page=0,
            min_price=60000,
            max_price=70000,
            location_ids=[174, 175, 176, 177, 178, 179]  # All Jakarta areas
        )
        
        # Verify all parameters are present
        self.assertIn('q=semen+gresik+40kg', url)
        self.assertIn('ob=3', url)
        self.assertIn('pmin=60000', url)
        self.assertIn('pmax=70000', url)
        self.assertIn('fcity=174%2C175%2C176%2C177%2C178%2C179', url)
        
        # Verify URL is well-formed
        parsed = urlparse(url)
        self.assertTrue(parsed.scheme)
        self.assertTrue(parsed.netloc)
        self.assertTrue(parsed.path)
        self.assertTrue(parsed.query)


if __name__ == '__main__':
    unittest.main()
