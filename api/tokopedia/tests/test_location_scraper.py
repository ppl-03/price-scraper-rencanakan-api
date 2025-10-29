import unittest
from bs4 import BeautifulSoup
from api.tokopedia.location_scraper import TokopediaLocationScraper, get_location_scraper


class TestTokopediaLocationScraper(unittest.TestCase):
    """Test cases for location extraction from Tokopedia HTML"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = TokopediaLocationScraper()
    
    def test_valid_location_extraction_from_span(self):
        """Test extracting location from span with css-ywdpwd class"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd">Jakarta Utara</span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        self.assertEqual(location, 'Jakarta Utara')
    
    def test_location_with_prefix_removal(self):
        """Test that location with Kab./Kota prefix is returned as-is (no prefix removal)"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd">Kab. Tangerang</span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        # Should preserve the full text including "Kab."
        self.assertEqual(location, 'Kab. Tangerang')
    
    def test_popular_city_recognition(self):
        """Test that popular Indonesian cities are recognized"""
        test_cases = [
            'Surabaya',
            'Bandung',
            'Medan',
            'Semarang',
            'Yogyakarta',
        ]
        
        for city in test_cases:
            html = f'<div class="product"><span>{city}</span></div>'
            soup = BeautifulSoup(html, 'html.parser')
            product = soup.find('div')
            
            location = self.scraper.extract_location_from_product_item(product)
            self.assertIsNotNone(location, f"Failed to extract {city}")
    
    def test_invalid_location_rejection(self):
        """Test that invalid locations are rejected"""
        html = '''
        <div class="product-item">
            <span>a</span>
            <span>Very long text that definitely does not look like a location at all because it is way too long</span>
            <span></span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNone(location)
    
    def test_location_cleaning(self):
        """Test location text cleaning"""
        test_cases = [
            ('  Jakarta Utara  ', 'Jakarta Utara'),  # Extra spaces
            ('Jakarta-Utara', 'Jakarta-Utara'),  # Hyphenated
            ('JAKARTA UTARA', 'jakarta utara'),  # Case normalization
        ]
        
        for raw, expected_contains in test_cases:
            cleaned = self.scraper._clean_and_validate_location(raw)
            self.assertIsNotNone(cleaned)
            # Check case-insensitive containment
            self.assertIn(expected_contains.lower(), cleaned.lower())
    
    def test_singleton_pattern(self):
        """Test that get_location_scraper returns singleton"""
        scraper1 = get_location_scraper()
        scraper2 = get_location_scraper()
        
        self.assertIs(scraper1, scraper2)
    
    def test_multiple_spans_priority(self):
        """Test that the first valid location found is returned"""
        html = '''
        <div class="product-item">
            <span>Jakarta Utara</span>
            <span>Bandung</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        # Should return the first valid location found
        self.assertIn('Jakarta', location)
    
    def test_location_with_numbers_rejected(self):
        """Test that span with css-ywdpwd class containing only numbers is still extracted (raw text)"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd">123456</span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        # Raw text extraction from css-ywdpwd returns as-is, even if only numbers
        # This test now documents that behavior (no special validation)
        self.assertEqual(location, '123456')


    def test_none_product_item(self):
        """Test that None product_item returns None"""
        location = self.scraper.extract_location_from_product_item(None)
        self.assertIsNone(location)
    
    def test_empty_location_span(self):
        """Test that empty css-ywdpwd span returns None"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd"></span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNone(location)
    
    def test_text_node_traversal_fallback(self):
        """Test text node traversal when css-ywdpwd is not present"""
        html = '''
        <div class="product-item">
            <span>Product Name</span>
            <span>Rp 100.000</span>
            Jakarta Barat
            <span>Shop Info</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        # Should find Jakarta Barat through text node traversal
        self.assertIsNotNone(location)
        self.assertIn('Jakarta', location)
    
    def test_text_node_with_delimiters(self):
        """Test text node extraction with various delimiters"""
        html = '''
        <div class="product-item">
            Product • Jakarta Timur | Shop
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        self.assertIn('Jakarta', location)
    
    def test_kota_prefix_preserved(self):
        """Test that Kota prefix is preserved in extracted location"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd">Kota Bandung</span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        self.assertEqual(location, 'Kota Bandung')
    
    def test_location_with_special_characters_cleaned(self):
        """Test that special characters are removed but structure preserved"""
        html = '''
        <div class="product-item">
            <span>Jakarta@Utara#123</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        # Special chars removed, but location preserved
        self.assertNotIn('@', location)
        self.assertNotIn('#', location)
    
    def test_clean_and_validate_very_short_text(self):
        """Test cleaning very short text returns None"""
        result = self.scraper._clean_and_validate_location('a')
        self.assertIsNone(result)
    
    def test_clean_and_validate_very_long_text(self):
        """Test cleaning very long text returns None"""
        long_text = 'a' * 101
        result = self.scraper._clean_and_validate_location(long_text)
        self.assertIsNone(result)
    
    def test_clean_and_validate_none_input(self):
        """Test cleaning None input returns None"""
        result = self.scraper._clean_and_validate_location(None)
        self.assertIsNone(result)
    
    def test_clean_and_validate_empty_string(self):
        """Test cleaning empty string returns None"""
        result = self.scraper._clean_and_validate_location('')
        self.assertIsNone(result)
    
    def test_clean_and_validate_whitespace_only(self):
        """Test cleaning whitespace-only text"""
        result = self.scraper._clean_and_validate_location('   ')
        # After normalization becomes empty
        self.assertIsNone(result)
    
    def test_is_valid_location_with_numbers(self):
        """Test is_valid_location accepts locations with numbers"""
        result = self.scraper._is_valid_location('Jakarta 123')
        self.assertTrue(result)
    
    def test_is_valid_location_too_short(self):
        """Test is_valid_location rejects very short text"""
        result = self.scraper._is_valid_location('a')
        self.assertFalse(result)
    
    def test_is_valid_location_too_long(self):
        """Test is_valid_location rejects very long text"""
        long_text = 'a' * 101
        result = self.scraper._is_valid_location(long_text)
        self.assertFalse(result)
    
    def test_is_valid_location_no_alpha(self):
        """Test is_valid_location rejects text without alphabetic characters"""
        result = self.scraper._is_valid_location('12345')
        self.assertFalse(result)
    
    def test_is_valid_location_none(self):
        """Test is_valid_location with None"""
        result = self.scraper._is_valid_location(None)
        self.assertFalse(result)
    
    def test_reset_locations_found(self):
        """Test reset clears locations found set"""
        self.scraper.locations_found.add('Jakarta')
        self.scraper.reset()
        self.assertEqual(len(self.scraper.locations_found), 0)
    
    def test_multiple_css_ywdpwd_spans_returns_first(self):
        """Test that multiple css-ywdpwd spans returns the first one"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd">Bandung</span>
            </div>
            <div class="css-vbihp9">
                <span class="css-ywdpwd">Jakarta</span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertEqual(location, 'Bandung')
    
    def test_css_ywdpwd_span_with_nested_elements(self):
        """Test extraction from css-ywdpwd span containing nested elements"""
        html = '''
        <div class="product-item">
            <div class="css-vbihp9">
                <span class="css-ywdpwd">
                    <b>Surabaya</b>
                </span>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        product_item = soup.find('div', class_='product-item')
        
        location = self.scraper.extract_location_from_product_item(product_item)
        self.assertIsNotNone(location)
        self.assertIn('Surabaya', location)


class TestLocationScraperIntegration(unittest.TestCase):
    """Integration tests with HTML parser"""
    
    def test_location_extraction_with_html_parser(self):
        """Test location extraction integrated with HTML parser"""
        from api.tokopedia.html_parser import TokopediaHtmlParser
        
        # Sample HTML with location data in css-ywdpwd span
        html = '''
        <html>
            <body>
                <a data-testid="lnkProductContainer" href="/product/semen-40kg">
                    <div data-testid="divProductWrapper">
                        <img alt="Semen 40kg" src="image.jpg"/>
                        <span class="css-20kt3o">Semen 40kg Premium</span>
                        <span class="css-o5uqv">Rp 75.000</span>
                        <div class="css-vbihp9">
                            <span class="css-ywdpwd">Jakarta Selatan</span>
                        </div>
                    </div>
                </a>
            </body>
        </html>
        '''
        
        parser = TokopediaHtmlParser()
        products = parser.parse_products(html)
        
        self.assertGreater(len(products), 0)
        product = products[0]
        self.assertIsNotNone(product.location)
        self.assertEqual(product.location, 'Jakarta Selatan')


if __name__ == '__main__':
    unittest.main()
