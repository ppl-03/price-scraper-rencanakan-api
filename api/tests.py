from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, Client
from .scraper import clean_price_gemilang, scrape_products_from_gemilang_html, clean_price_depo, scrape_products_from_depo_html, scrape_products_from_depo_html, clean_price_juraganmaterial, scrape_products_from_juraganmaterial_html, clean_price_mitra10, scrape_products_from_mitra10_html
from .interfaces import Product, ScrapingResult, HttpClientError, UrlBuilderError, HtmlParserError
from .services import (
    RequestsHttpClient, GemilangUrlBuilder, GemilangHtmlParser, 
    GemilangPriceScraper, create_gemilang_scraper
)

class ScraperLogicTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "tests/fixtures/gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
        depo_fp = base / "tests/fixtures/depo_mock_results.html"
        cls.mock_html_depo = depo_fp.read_text(encoding="utf-8")
        juragan_fp = base / "tests/fixtures/juraganmaterial_mock_results.html"
        cls.mock_html_juragan = juragan_fp.read_text(encoding="utf-8")
        mitra_fp = base / "tests/fixtures/mitra10_mock_results.html"
        cls.mock_html_mitra = mitra_fp.read_text(encoding="utf-8")

    def test_clean_price(self):
        cleaned_price = clean_price_gemilang("Rp 55.000")
        self.assertEqual(cleaned_price, 55000)
    
    def test_clean_price_depo(self):
        cleaned_price = clean_price_depo("Rp 125.000")
        self.assertEqual(cleaned_price, 125000)
    
    def test_clean_price_juraganmaterial(self):
        cleaned_price = clean_price_juraganmaterial("Rp 75.000")
        self.assertEqual(cleaned_price, 75000)

    def test_clean_price_mitra10(self):
        cleaned_price = clean_price_mitra10("IDR 12,000")
        self.assertEqual(cleaned_price, 12000)

    def test_scrape_juraganmaterial(self):
        """Test only Juragan Material scraper functionality"""
        products_juragan = scrape_products_from_juraganmaterial_html(self.mock_html_juragan)
        self.assertIsInstance(products_juragan, list)
        self.assertEqual(len(products_juragan), 3)
        self.assertEqual(products_juragan[0]["name"], "Semen Holcim 40Kg")
        self.assertEqual(products_juragan[0]["price"], 60500)
        self.assertEqual(products_juragan[0]["url"], "/products/semen-holcim-40kg")

    def test_scrape_products_returns_a_list(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 2)

        products_depo = scrape_products_from_depo_html(self.mock_html_depo)
        self.assertIsInstance(products_depo, list)
        self.assertEqual(len(products_depo), 2)
        self.assertEqual(products_depo[0]["name"], "Produk A")
        self.assertEqual(products_depo[0]["price"], 3600)
        self.assertTrue(products_depo[0]["url"]) 

        products_mitra10 = scrape_products_from_mitra10_html(self.mock_html_mitra)
        self.assertIsInstance(products_mitra10, list)
        self.assertEqual(len(products_mitra10), 2)
        self.assertEqual(products_mitra10[0]["name"], "Demix Nat Ubin Dasar 1 Kg Ungu Borneo")
        self.assertEqual(products_mitra10[0]["price"], 12000)
        self.assertTrue(products_mitra10[0]["url"])

class ScraperAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_endpoint = '/api/scrape/'

    def test_api_juraganmaterial_scraper_function_exists(self):
        """Test that Juragan Material scraper function exists and works"""
        from .scraper import scrape_products_from_juraganmaterial_html
        
        # Test with empty HTML to ensure function exists and returns list
        result = scrape_products_from_juraganmaterial_html("")
        self.assertIsInstance(result, list)

    def test_api_requires_keyword(self):
        response = self.client.get(self.api_endpoint)
        self.assertEqual(response.status_code, 404)


class GemilangPriceCleaningTests(TestCase):

    def test_clean_price_gemilang_standard_format(self):
        result = clean_price_gemilang("Rp 55.000")
        self.assertEqual(result, 55000)

    def test_clean_price_gemilang_no_dots(self):
        result = clean_price_gemilang("Rp 55000")
        self.assertEqual(result, 55000)

    def test_clean_price_gemilang_with_commas(self):
        result = clean_price_gemilang("Rp 55,000")
        self.assertEqual(result, 55000)

    def test_clean_price_gemilang_mixed_separators(self):
        result = clean_price_gemilang("Rp 1.250,50")
        self.assertEqual(result, 125050)

    def test_clean_price_gemilang_no_currency(self):
        result = clean_price_gemilang("55000")
        self.assertEqual(result, 55000)

    def test_clean_price_gemilang_empty_string(self):
        result = clean_price_gemilang("")
        self.assertEqual(result, 0)

    def test_clean_price_gemilang_no_digits(self):
        result = clean_price_gemilang("Rp")
        self.assertEqual(result, 0)

    def test_clean_price_gemilang_whitespace(self):
        result = clean_price_gemilang("  Rp 55.000  ")
        self.assertEqual(result, 55000)

    def test_clean_price_gemilang_large_numbers(self):
        result = clean_price_gemilang("Rp 1.500.000")
        self.assertEqual(result, 1500000)

    def test_clean_price_gemilang_returns_integer(self):
        result = clean_price_gemilang("Rp 100")
        self.assertIsInstance(result, int)


class GemilangHTMLParsingTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "tests/fixtures/gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")

    def test_scrape_gemilang_valid_products(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 2)

    def test_scrape_gemilang_empty_html(self):
        products = scrape_products_from_gemilang_html("")
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 0)

    def test_scrape_gemilang_no_products(self):
        html = "<html><body><div>No products here</div></body></html>"
        products = scrape_products_from_gemilang_html(html)
        self.assertIsInstance(products, list)
        self.assertEqual(len(products), 0)

    def test_scrape_gemilang_malformed_html(self):
        html = "<html><body><div class='item-product'><p>Broken"
        products = scrape_products_from_gemilang_html(html)
        self.assertIsInstance(products, list)

    def test_scrape_gemilang_missing_name(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/test-product">
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 10.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 0)

    def test_scrape_gemilang_missing_price(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="price-wrapper">
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 0)

    def test_scrape_gemilang_missing_url(self):
        html = '''
        <div class="item-product">
            <p class="product-name">Test Product</p>
            <div class="price-wrapper">
                <p class="price">Rp 10.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 0)

    def test_scrape_gemilang_multiple_products(self):
        html = '''
        <div class="product-list">
            <div class="item-product">
                <a href="/pusat/product-1">
                    <p class="product-name">Product 1</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">Rp 10.000</p>
                </div>
            </div>
            <div class="item-product">
                <a href="/pusat/product-2">
                    <p class="product-name">Product 2</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">Rp 20.000</p>
                </div>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]['name'], 'Product 1')
        self.assertEqual(products[0]['price'], 10000)
        self.assertEqual(products[0]['url'], '/pusat/product-1')
        self.assertEqual(products[1]['name'], 'Product 2')
        self.assertEqual(products[1]['price'], 20000)
        self.assertEqual(products[1]['url'], '/pusat/product-2')

    def test_scrape_gemilang_zero_price(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 0</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 0)

    def test_gemilang_product_name_exact_match(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/exact-product-name">
                <p class="product-name">Exact Product Name</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 15.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], 'Exact Product Name')

    def test_gemilang_product_name_with_special_characters(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/special-product">
                <p class="product-name">Product & Tools 100%</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 25.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], 'Product & Tools 100%')

    def test_gemilang_product_name_with_numbers(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/numbered-product">
                <p class="product-name">Cat Tembok 5Kg Premium 2024</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 45.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], 'Cat Tembok 5Kg Premium 2024')

    def test_gemilang_product_name_with_whitespace(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/whitespace-product">
                <p class="product-name">  Product With Spaces  </p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 12.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], 'Product With Spaces')


class GemilangDataValidationTests(TestCase):

    def setUp(self):
        self.valid_html = '''
        <div class="item-product">
            <a href="/pusat/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 10.000</p>
            </div>
        </div>
        '''

    def test_gemilang_product_structure(self):
        products = scrape_products_from_gemilang_html(self.valid_html)
        if products:
            product = products[0]
            self.assertIn('name', product)
            self.assertIn('price', product)
            self.assertIn('url', product)

    def test_gemilang_data_types(self):
        products = scrape_products_from_gemilang_html(self.valid_html)
        if products:
            product = products[0]
            self.assertIsInstance(product['price'], int)
            self.assertIsInstance(product['name'], str)
            self.assertIsInstance(product['url'], str)

    def test_gemilang_name_not_empty(self):
        products = scrape_products_from_gemilang_html(self.valid_html)
        for product in products:
            self.assertTrue(product['name'].strip())

    def test_gemilang_price_positive(self):
        products = scrape_products_from_gemilang_html(self.valid_html)
        for product in products:
            self.assertGreater(product['price'], 0)

    def test_gemilang_url_not_empty(self):
        products = scrape_products_from_gemilang_html(self.valid_html)
        for product in products:
            self.assertTrue(product['url'])


class GemilangErrorHandlingTests(TestCase):

    def test_gemilang_none_input(self):
        with self.assertRaises(AttributeError):
            scrape_products_from_gemilang_html(None)

    def test_gemilang_price_none_input(self):
        with self.assertRaises(TypeError):
            clean_price_gemilang(None)

    def test_gemilang_price_non_string_input(self):
        with self.assertRaises(TypeError):
            clean_price_gemilang(123)

    def test_gemilang_encoding_issues(self):
        html_with_special_chars = '''
        <div class="item-product">
            <a href="/pusat/test-product">
                <p class="product-name">Prodük Spëcial</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 10.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html_with_special_chars)
        self.assertIsInstance(products, list)


class GemilangAcceptanceCriteriaTests(TestCase):

    def setUp(self):
        self.sample_html = '''
        <div class="product-list">
            <div class="item-product">
                <a href="/pusat/cheap-product">
                    <p class="product-name">Cheap Product</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">Rp 10.000</p>
                </div>
            </div>
            <div class="item-product">
                <a href="/pusat/expensive-product">
                    <p class="product-name">Expensive Product</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">Rp 50.000</p>
                </div>
            </div>
        </div>
        '''

    def test_ac1_consistent_scraping(self):
        products1 = scrape_products_from_gemilang_html(self.sample_html)
        products2 = scrape_products_from_gemilang_html(self.sample_html)
        self.assertEqual(products1, products2)

    def test_ac2_price_comparison_ready(self):
        products = scrape_products_from_gemilang_html(self.sample_html)
        for product in products:
            self.assertIsInstance(product['price'], int)
            self.assertGreater(product['price'], 0)

    def test_ac2_cheapest_detection(self):
        products = scrape_products_from_gemilang_html(self.sample_html)
        if len(products) > 1:
            cheapest = min(products, key=lambda x: x['price'])
            self.assertEqual(cheapest['name'], 'Cheap Product')
            self.assertEqual(cheapest['price'], 10000)

    def test_ac3_empty_results_handling(self):
        empty_html = "<html><body>No products</body></html>"
        products = scrape_products_from_gemilang_html(empty_html)
        self.assertEqual(products, [])

    def test_ac6_standardized_response_format(self):
        products = scrape_products_from_gemilang_html(self.sample_html)
        expected_keys = {'name', 'price', 'url'}
        for product in products:
            self.assertEqual(set(product.keys()), expected_keys)


class GemilangFixtureTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "tests/fixtures/gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")

    def test_gemilang_fixture_parsing(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        self.assertIsInstance(products, list)

    def test_gemilang_fixture_product_count(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        self.assertEqual(len(products), 2)

    def test_gemilang_fixture_specific_products(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        if len(products) >= 2:
            self.assertEqual(products[0]['name'], 'GML KUAS CAT 1inch')
            self.assertEqual(products[0]['price'], 3600)
            self.assertEqual(products[0]['url'], '/pusat/gml-kuas-cat-1inch')
            
            self.assertEqual(products[1]['name'], 'Cat Tembok Spectrum 5Kg')
            self.assertEqual(products[1]['price'], 55000)
            self.assertEqual(products[1]['url'], '/pusat/cat-tembok-spectrum-5kg')

    def test_gemilang_fixture_price_extraction(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        expected_prices = [3600, 55000]
        actual_prices = [product['price'] for product in products]
        self.assertEqual(sorted(actual_prices), sorted(expected_prices))

    def test_gemilang_fixture_name_extraction(self):
        products = scrape_products_from_gemilang_html(self.mock_html)
        expected_names = ['GML KUAS CAT 1inch', 'Cat Tembok Spectrum 5Kg']
        actual_names = [product['name'] for product in products]
        self.assertEqual(sorted(actual_names), sorted(expected_names))


class GemilangStructureSpecificTests(TestCase):

    def test_gemilang_documented_path_structure(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/test-product">
                <p class="product-name">Test Product</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 25.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['price'], 25000)

    def test_gemilang_url_path_format(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/gml-kuas-cat-1inch">
                <p class="product-name">GML KUAS CAT 1inch</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 3.600</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['url'], '/pusat/gml-kuas-cat-1inch')
        self.assertTrue(products[0]['url'].startswith('/pusat/'))

    def test_gemilang_product_name_extraction(self):
        html = '''
        <div class="item-product">
            <a href="/pusat/cat-tembok-spectrum-5kg">
                <p class="product-name">Cat Tembok Spectrum 5Kg</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 55.000</p>
            </div>
        </div>
        '''
        products = scrape_products_from_gemilang_html(html)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], 'Cat Tembok Spectrum 5Kg')

    def test_gemilang_price_format_variations(self):
        test_cases = [
            ('Rp 3.600', 3600),
            ('Rp 55.000', 55000),
            ('Rp 1.250.000', 1250000),
            ('Rp 15.500', 15500)
        ]
        
        for price_text, expected_price in test_cases:
            html = f'''
            <div class="item-product">
                <a href="/pusat/test-product">
                    <p class="product-name">Test Product</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">{price_text}</p>
                </div>
            </div>
            '''
            products = scrape_products_from_gemilang_html(html)
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0]['price'], expected_price)

    def test_gemilang_container_variations(self):
        html_no_container = '''
        <div class="item-product">
            <a href="/pusat/product1">
                <p class="product-name">Product 1</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 10.000</p>
            </div>
        </div>
        '''
        
        html_with_container = '''
        <div class="product-list">
            <div class="item-product">
                <a href="/pusat/product1">
                    <p class="product-name">Product 1</p>
                </a>
                <div class="price-wrapper">
                    <p class="price">Rp 10.000</p>
                </div>
            </div>
        </div>
        '''
        
        products_no_container = scrape_products_from_gemilang_html(html_no_container)
        products_with_container = scrape_products_from_gemilang_html(html_with_container)
        
        self.assertEqual(len(products_no_container), 1)
        self.assertEqual(len(products_with_container), 1)
        self.assertEqual(products_no_container[0]['name'], products_with_container[0]['name'])

    def test_gemilang_search_url_compatibility(self):
        products = scrape_products_from_gemilang_html('''
        <div class="item-product">
            <a href="/pusat/cat-tembok-spectrum-5kg">
                <p class="product-name">Cat Tembok Spectrum 5Kg</p>
            </a>
            <div class="price-wrapper">
                <p class="price">Rp 55.000</p>
            </div>
        </div>
        ''')
        
        if products:
            product = products[0]
            self.assertIn('name', product)
            self.assertIn('price', product)
            self.assertIn('url', product)
            self.assertIsInstance(product['price'], int)
            self.assertTrue(product['url'].startswith('/pusat/'))


class TestGemilangIntegration(TestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = Path(__file__).parent
        fixture_path = base / "tests/fixtures/gemilang_mock_results.html"
        cls.mock_html = fixture_path.read_text(encoding="utf-8")
    
    def setUp(self):
        self.mock_http_client = Mock(spec=RequestsHttpClient)
        self.url_builder = GemilangUrlBuilder()
        self.html_parser = GemilangHtmlParser()
        self.scraper = GemilangPriceScraper(
            self.mock_http_client, 
            self.url_builder, 
            self.html_parser
        )
    
    def test_complete_scraping_pipeline_success(self):
        keyword = "cat"
        self.mock_http_client.get.return_value = self.mock_html
        
        result = self.scraper.scrape_products(keyword)
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertIsNotNone(result.url)
        self.assertIn("keyword=cat", result.url)
        self.assertIn("sort=price_asc", result.url)
        
        self.assertEqual(len(result.products), 2)
        
        product1 = result.products[0]
        self.assertEqual(product1.name, "GML KUAS CAT 1inch")
        self.assertEqual(product1.price, 3600)
        self.assertEqual(product1.url, "/pusat/gml-kuas-cat-1inch")
        
        product2 = result.products[1]
        self.assertEqual(product2.name, "Cat Tembok Spectrum 5Kg")
        self.assertEqual(product2.price, 55000)
        self.assertEqual(product2.url, "/pusat/cat-tembok-spectrum-5kg")
        
        self.mock_http_client.get.assert_called_once()
        called_url = self.mock_http_client.get.call_args[0][0]
        self.assertIn("keyword=cat", called_url)
    
    def test_scraping_with_pagination(self):
        keyword = "semen"
        page = 2
        self.mock_http_client.get.return_value = self.mock_html
        
        result = self.scraper.scrape_products(keyword, sort_by_price=False, page=page)
        
        self.assertTrue(result.success)
        self.assertIn("keyword=semen", result.url)
        self.assertIn("page=2", result.url)
        self.assertNotIn("sort=price_asc", result.url)
    
    def test_scraping_with_http_error(self):
        keyword = "cat"
        self.mock_http_client.get.side_effect = HttpClientError("Connection timeout")
        
        result = self.scraper.scrape_products(keyword)
        
        self.assertFalse(result.success)
        self.assertIn("Connection timeout", result.error_message)
        self.assertEqual(len(result.products), 0)
    
    def test_scraping_with_empty_html(self):
        keyword = "cat"
        self.mock_http_client.get.return_value = ""
        
        result = self.scraper.scrape_products(keyword)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
    
    def test_scraping_with_no_products_found(self):
        keyword = "cat"
        html_no_products = "<html><body><div>No products found</div></body></html>"
        self.mock_http_client.get.return_value = html_no_products
        
        result = self.scraper.scrape_products(keyword)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 0)
    
    def test_invalid_keyword_handling(self):
        result = self.scraper.scrape_products("")
        self.assertFalse(result.success)
        self.assertIn("Keyword cannot be empty", result.error_message)
        
        result = self.scraper.scrape_products("   ")
        self.assertFalse(result.success)
        self.assertIn("Keyword cannot be empty", result.error_message)
    
    def test_factory_function(self):
        scraper = create_gemilang_scraper()
        
        self.assertIsInstance(scraper, GemilangPriceScraper)
        self.assertIsNotNone(scraper.http_client)
        self.assertIsNotNone(scraper.url_builder)
        self.assertIsNotNone(scraper.html_parser)