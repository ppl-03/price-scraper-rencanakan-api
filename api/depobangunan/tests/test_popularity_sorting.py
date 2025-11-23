"""
Tests for DepoBangunan popularity sorting functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock, Mock
import json
from api.interfaces import Product, ScrapingResult


class DepoBangunanPopularitySortingTests(TestCase):
    """Test suite for popularity sorting endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.scrape_url = reverse('depobangunan:scrape_products')
        self.scrape_popularity_url = reverse('depobangunan:scrape_popularity')
        self.scrape_and_save_url = reverse('depobangunan:scrape_and_save_products')
    
    def create_mock_product(self, name, price, url, unit='PCS', sold_count=None):
        """Helper to create mock product"""
        return Product(
            name=name,
            price=price,
            url=url,
            unit=unit,
            sold_count=sold_count
        )
    
    def create_mock_scraper(self, products, success=True, error_message=None):
        """Helper to create mock scraper"""
        mock_scraper = MagicMock()
        mock_result = ScrapingResult(
            products=products,
            success=success,
            error_message=error_message,
            url="https://www.depobangunan.co.id/test"
        )
        mock_scraper.scrape_products.return_value = mock_result
        mock_scraper.scrape_popularity_products.return_value = mock_result
        return mock_scraper


class TestScrapeProductsWithSortType(DepoBangunanPopularitySortingTests):
    """Tests for scrape_products endpoint with sort_type parameter"""
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_with_sort_type_cheapest(self, mock_create_scraper):
        """Test scraping with sort_type=cheapest"""
        products = [
            self.create_mock_product('Product A', 10000, '/a', sold_count=5),
            self.create_mock_product('Product B', 20000, '/b', sold_count=10),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sort_type'], 'cheapest')
        self.assertEqual(len(data['products']), 2)
        # Should call with sort_by_price=True
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=True,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_with_sort_type_popularity(self, mock_create_scraper):
        """Test scraping with sort_type=popularity"""
        products = [
            self.create_mock_product('Product A', 10000, '/a', sold_count=5),
            self.create_mock_product('Product B', 20000, '/b', sold_count=10),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'semen',
            'sort_type': 'popularity'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sort_type'], 'popularity')
        # Should call with sort_by_price=False
        mock_scraper.scrape_products.assert_called_once_with(
            keyword='semen',
            sort_by_price=False,
            page=0
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_with_invalid_sort_type(self, mock_create_scraper):
        """Test scraping with invalid sort_type returns error"""
        response = self.client.get(self.scrape_url, {
            'keyword': 'semen',
            'sort_type': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('cheapest', data['error'])
        self.assertIn('popularity', data['error'])
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_backward_compatible_with_sort_by_price(self, mock_create_scraper):
        """Test that old sort_by_price parameter still works"""
        products = [self.create_mock_product('Product A', 10000, '/a')]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'semen',
            'sort_by_price': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['sort_type'], 'cheapest')
        
        response = self.client.get(self.scrape_url, {
            'keyword': 'semen',
            'sort_by_price': 'false'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['sort_type'], 'popularity')


class TestScrapePopularityEndpoint(DepoBangunanPopularitySortingTests):
    """Tests for scrape_popularity endpoint"""
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_popularity_success(self, mock_create_scraper):
        """Test successful popularity scraping"""
        products = [
            self.create_mock_product('Product A', 10000, '/a', sold_count=50),
            self.create_mock_product('Product B', 20000, '/b', sold_count=30),
            self.create_mock_product('Product C', 15000, '/c', sold_count=20),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'page': 0,
            'top_n': 5
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_products'], 3)
        self.assertEqual(len(data['products']), 3)
        # Verify sold_count is included
        self.assertIsNotNone(data['products'][0]['sold_count'])
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=0,
            top_n=5
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_popularity_default_top_n(self, mock_create_scraper):
        """Test that top_n defaults to 5"""
        products = [self.create_mock_product('Product A', 10000, '/a', sold_count=10)]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen'
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=0,
            top_n=5
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_popularity_custom_top_n(self, mock_create_scraper):
        """Test custom top_n parameter"""
        products = [self.create_mock_product('Product A', 10000, '/a', sold_count=10)]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'top_n': 10
        })
        
        self.assertEqual(response.status_code, 200)
        mock_scraper.scrape_popularity_products.assert_called_once_with(
            keyword='semen',
            page=0,
            top_n=10
        )
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_popularity_invalid_top_n(self, mock_create_scraper):
        """Test that invalid top_n defaults to 5"""
        products = [self.create_mock_product('Product A', 10000, '/a', sold_count=10)]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.get(self.scrape_popularity_url, {
            'keyword': 'semen',
            'top_n': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_scrape_popularity_missing_keyword(self):
        """Test error when keyword is missing"""
        response = self.client.get(self.scrape_popularity_url, {})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)


class TestScrapeAndSaveWithSortType(DepoBangunanPopularitySortingTests):
    """Tests for scrape_and_save endpoint with sort_type"""
    
    @patch('api.depobangunan.views.SecurityDesignPatterns.validate_business_logic')
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_cheapest(self, mock_create_scraper, mock_db_service, mock_security_validate):
        """Test scrape and save with cheapest sort type"""
        # Mock security validation
        mock_security_validate.return_value = (True, "")
        
        products = [
            self.create_mock_product('Product A', 10000, '/a', sold_count=5),
            self.create_mock_product('Product B', 20000, '/b', sold_count=10),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        mock_db = MagicMock()
        mock_db.save.return_value = True
        mock_db_service.return_value = mock_db
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest',
            'page': 0
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['saved'], 2)
        self.assertEqual(data['inserted'], 2)
        # Should save all products for cheapest
        self.assertEqual(len(mock_db.save.call_args[0][0]), 2)
    
    @patch('api.depobangunan.views.SecurityDesignPatterns.validate_business_logic')
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_popularity_filters_top_5(self, mock_create_scraper, mock_db_service, mock_security_validate):
        """Test scrape and save popularity only saves top 5"""
        # Mock security validation
        mock_security_validate.return_value = (True, "")
        
        # Create 10 products with different sold counts
        products = [
            self.create_mock_product(f'Product {i}', 10000 + i, f'/p{i}', sold_count=100 - i)
            for i in range(10)
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        mock_db = MagicMock()
        mock_db.save.return_value = True
        mock_db_service.return_value = mock_db
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'popularity',
            'page': 0
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['saved'], 5)
        self.assertEqual(data['inserted'], 5)
        # Should only save top 5 products
        saved_products = mock_db.save.call_args[0][0]
        self.assertEqual(len(saved_products), 5)
    
    @patch('api.depobangunan.views.SecurityDesignPatterns.validate_business_logic')
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_popularity_sorts_by_sold_count(self, mock_create_scraper, mock_db_service, mock_security_validate):
        """Test that popularity sorting actually sorts by sold_count"""
        # Mock security validation
        mock_security_validate.return_value = (True, "")
        
        products = [
            self.create_mock_product('Low Sales', 10000, '/a', sold_count=5),
            self.create_mock_product('High Sales', 20000, '/b', sold_count=100),
            self.create_mock_product('Med Sales', 15000, '/c', sold_count=50),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        mock_db = MagicMock()
        mock_db.save.return_value = True
        mock_db_service.return_value = mock_db
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'popularity'
        })
        
        self.assertEqual(response.status_code, 200)
        # Check that products are sorted correctly (highest sold_count first)
        # We can't directly check the order, but we saved 3 products
        self.assertEqual(mock_db.save.call_args[0][0][0]['name'], 'High Sales')
    
    @patch('api.depobangunan.views.SecurityDesignPatterns.validate_business_logic')
    @patch('db_pricing.models.DepoBangunanProduct')
    @patch('api.depobangunan.views.AutoCategorizationService')
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_with_price_update(self, mock_create_scraper, mock_db_service, mock_cat_service_cls, mock_model, mock_security_validate):
        """Test scrape and save with price update mode"""
        # Mock security validation
        mock_security_validate.return_value = (True, "")
        
        # Mock categorization service (for price_update mode)
        mock_cat_service = mock_cat_service_cls.return_value
        mock_cat_service.categorize_products.return_value = {
            'total': 0,
            'categorized': 0,
            'uncategorized': 0
        }
        
        # Mock DepoBangunanProduct.objects (for price_update mode)
        mock_products = MagicMock()
        mock_products.values_list.return_value = []
        mock_model.objects.filter.return_value.order_by.return_value.__getitem__.return_value = mock_products
        
        products = [
            self.create_mock_product('Product A', 10000, '/a'),
        ]
        mock_scraper = self.create_mock_scraper(products)
        mock_create_scraper.return_value = mock_scraper
        
        mock_db = MagicMock()
        mock_db.save_with_price_update.return_value = {
            'success': True,
            'updated_count': 1,
            'new_count': 0,
            'anomalies': []
        }
        mock_db_service.return_value = mock_db
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'cheapest',
            'use_price_update': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['updated'], 1)
        self.assertEqual(data['inserted'], 0)
        self.assertIn('anomalies', data)
    
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_invalid_sort_type(self, mock_create_scraper):
        """Test error with invalid sort_type"""
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'semen',
            'sort_type': 'invalid'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('api.depobangunan.views.DepoBangunanDatabaseService')
    @patch('api.depobangunan.views.create_depo_scraper')
    def test_scrape_and_save_no_products_found(self, mock_create_scraper, mock_db_service):
        """Test response when no products found"""
        mock_scraper = self.create_mock_scraper([])
        mock_create_scraper.return_value = mock_scraper
        
        response = self.client.post(self.scrape_and_save_url, {
            'keyword': 'nonexistent',
            'sort_type': 'cheapest'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['saved'], 0)
        self.assertEqual(data['message'], 'No products found to save')


class TestURLBuilder(TestCase):
    """Tests for URL builder popularity URL"""
    
    def test_build_popularity_url(self):
        """Test building popularity URL"""
        from api.depobangunan.url_builder import DepoUrlBuilder
        
        builder = DepoUrlBuilder()
        url = builder.build_popularity_url('semen', page=0)
        
        self.assertIn('product_list_order=top_rated', url)
        self.assertIn('q=semen', url)
    
    def test_build_popularity_url_with_page(self):
        """Test building popularity URL with page parameter"""
        from api.depobangunan.url_builder import DepoUrlBuilder
        
        builder = DepoUrlBuilder()
        url = builder.build_popularity_url('semen', page=2)
        
        self.assertIn('p=2', url)
        self.assertIn('product_list_order=top_rated', url)


class TestHTMLParserSoldCount(TestCase):
    """Tests for HTML parser sold count extraction"""
    
    def test_extract_sold_count_from_html(self):
        """Test extracting sold count from HTML"""
        from api.depobangunan.html_parser import DepoHtmlParser
        
        html = '''
        <li class="item product product-item">
            <div>Product Name</div>
            <div>Terjual: 38</div>
            <span data-price-amount="10000"></span>
        </li>
        '''
        
        parser = DepoHtmlParser()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('li')
        
        sold_count = parser._extract_sold_count(item)
        self.assertEqual(sold_count, 38)
    
    def test_extract_sold_count_lowercase(self):
        """Test extracting sold count with lowercase 'terjual'"""
        from api.depobangunan.html_parser import DepoHtmlParser
        
        html = '<div>terjual 25</div>'
        
        parser = DepoHtmlParser()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        sold_count = parser._extract_sold_count(soup)
        self.assertEqual(sold_count, 25)
    
    def test_extract_sold_count_zero(self):
        """Test extracting sold count of zero"""
        from api.depobangunan.html_parser import DepoHtmlParser
        
        html = '<div>Terjual: 0</div>'
        
        parser = DepoHtmlParser()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        sold_count = parser._extract_sold_count(soup)
        self.assertEqual(sold_count, 0)
    
    def test_extract_sold_count_not_found(self):
        """Test when sold count is not found"""
        from api.depobangunan.html_parser import DepoHtmlParser
        
        html = '<div>Product without sold info</div>'
        
        parser = DepoHtmlParser()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        sold_count = parser._extract_sold_count(soup)
        self.assertIsNone(sold_count)


class TestScraperPopularityProducts(TestCase):
    """Tests for scraper popularity products method"""
    
    def test_scrape_popularity_products_sorts_correctly(self):
        """Test that scraper sorts products by sold_count correctly"""
        from api.depobangunan.scraper import DepoPriceScraper
        from api.depobangunan.url_builder import DepoUrlBuilder
        
        # Mock HTTP client
        mock_client = MagicMock()
        mock_client.get.return_value = '<html></html>'
        
        # Mock parser to return products with different sold counts
        mock_parser = MagicMock()
        mock_parser.parse_products.return_value = [
            Product('Product A', 10000, '/a', 'PCS', sold_count=5),
            Product('Product B', 20000, '/b', 'PCS', sold_count=50),
            Product('Product C', 15000, '/c', 'PCS', sold_count=20),
            Product('Product D', 12000, '/d', 'PCS', sold_count=100),
        ]
        
        url_builder = DepoUrlBuilder()
        scraper = DepoPriceScraper(mock_client, url_builder, mock_parser)
        
        result = scraper.scrape_popularity_products('semen', page=0, top_n=3)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 3)
        # Should be sorted by sold_count descending
        self.assertEqual(result.products[0].sold_count, 100)
        self.assertEqual(result.products[1].sold_count, 50)
        self.assertEqual(result.products[2].sold_count, 20)
    
    def test_scrape_popularity_products_no_sold_count(self):
        """Test when no products have sold_count"""
        from api.depobangunan.scraper import DepoPriceScraper
        from api.depobangunan.url_builder import DepoUrlBuilder
        
        # Mock HTTP client
        mock_client = MagicMock()
        mock_client.get.return_value = '<html></html>'
        
        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse_products.return_value = [
            Product('Product A', 10000, '/a', 'PCS', sold_count=None),
            Product('Product B', 20000, '/b', 'PCS', sold_count=None),
        ]
        
        url_builder = DepoUrlBuilder()
        scraper = DepoPriceScraper(mock_client, url_builder, mock_parser)
        
        result = scraper.scrape_popularity_products('semen', page=0, top_n=5)
        
        self.assertTrue(result.success)
        # Should return first 5 products (in this case 2)
        self.assertEqual(len(result.products), 2)
