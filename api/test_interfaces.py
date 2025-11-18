import unittest
from unittest.mock import Mock

from api.interfaces import (
    Product, 
    ScrapingResult, 
    IHttpClient, 
    IUrlBuilder, 
    IHtmlParser, 
    IPriceScraper,
    HttpClientError,
    UrlBuilderError
)


class TestProduct(unittest.TestCase):
    def test_product_creation(self):
        product = Product(
            name="Test Product",
            price=10000,
            url="https://example.com/product"
        )
        
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.url, "https://example.com/product")
    
    def test_product_equality(self):
        product1 = Product("Test", 10000, "https://example.com")
        product2 = Product("Test", 10000, "https://example.com")
        product3 = Product("Different", 20000, "https://different.com")
        
        self.assertEqual(product1, product2)
        self.assertNotEqual(product1, product3)


class TestScrapingResult(unittest.TestCase):
    def test_scraping_result_success(self):
        products = [Product("Test", 10000, "https://example.com")]
        result = ScrapingResult(
            products=products,
            success=True,
            url="https://search.com"
        )
        
        self.assertEqual(len(result.products), 1)
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.url, "https://search.com")
    
    def test_scraping_result_failure(self):
        result = ScrapingResult(
            products=[],
            success=False,
            error_message="Network error",
            url="https://search.com"
        )
        
        self.assertEqual(len(result.products), 0)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Network error")
        self.assertEqual(result.url, "https://search.com")
    
    def test_scraping_result_default_values(self):
        result = ScrapingResult(products=[], success=True)
        
        self.assertIsNone(result.error_message)
        self.assertIsNone(result.url)


class TestInterfaceAbstractMethods(unittest.TestCase):
    
    def test_ihttp_client_get_abstract(self):
        with self.assertRaises(TypeError):
            IHttpClient()
    
    def test_iurl_builder_build_search_url_abstract(self):
        with self.assertRaises(TypeError):
            IUrlBuilder()
    
    def test_ihtml_parser_parse_products_abstract(self):
        with self.assertRaises(TypeError):
            IHtmlParser()
    
    def test_iprice_scraper_scrape_products_abstract(self):
        with self.assertRaises(TypeError):
            IPriceScraper()


class TestInterfaceImplementations(unittest.TestCase):
    
    def test_concrete_http_client_implementation(self):
        
        class ConcreteHttpClient(IHttpClient):
            def get(self, url: str, timeout: int = 30) -> str:
                return f"Response from {url}"
        
        client = ConcreteHttpClient()
        response = client.get("https://example.com")
        self.assertEqual(response, "Response from https://example.com")
    
    def test_concrete_url_builder_implementation(self):
        
        class ConcreteUrlBuilder(IUrlBuilder):
            def build_search_url(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> str:
                return f"https://example.com/search?q={keyword}&sort={sort_by_price}&page={page}"
        
        builder = ConcreteUrlBuilder()
        url = builder.build_search_url("test", True, 1)
        self.assertEqual(url, "https://example.com/search?q=test&sort=True&page=1")
    
    def test_concrete_html_parser_implementation(self):
        
        class ConcreteHtmlParser(IHtmlParser):
            def parse_products(self, html_content: str) -> list:
                return [Product("Test Product", 10000, "https://example.com")]
        
        parser = ConcreteHtmlParser()
        products = parser.parse_products("<html>test</html>")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Test Product")
    
    def test_concrete_price_scraper_implementation(self):
        
        class ConcretePriceScraper(IPriceScraper):
            def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
                products = [Product("Test", 10000, "https://example.com")]
                return ScrapingResult(products=products, success=True)
        
        scraper = ConcretePriceScraper()
        result = scraper.scrape_products("test")
        self.assertTrue(result.success)
        self.assertEqual(len(result.products), 1)


class TestExceptions(unittest.TestCase):
    def test_http_client_error_creation(self):
        error = HttpClientError("Network error")
        self.assertEqual(str(error), "Network error")
        self.assertIsInstance(error, Exception)
    
    def test_http_client_error_raising(self):
        with self.assertRaises(HttpClientError) as context:
            raise HttpClientError("Connection failed")
        
        self.assertEqual(str(context.exception), "Connection failed")
    
    def test_url_builder_error_creation(self):
        error = UrlBuilderError("Invalid URL")
        self.assertEqual(str(error), "Invalid URL")
        self.assertIsInstance(error, Exception)
    
    def test_url_builder_error_raising(self):
        with self.assertRaises(UrlBuilderError) as context:
            raise UrlBuilderError("Invalid parameters")
        
        self.assertEqual(str(context.exception), "Invalid parameters")
    
    def test_exception_inheritance(self):
        self.assertTrue(issubclass(HttpClientError, Exception))
        self.assertTrue(issubclass(UrlBuilderError, Exception))


class TestInterfaceMethodSignatures(unittest.TestCase):
    
    def test_ihttp_client_pass_statement_coverage(self):
        
        class PassTestClient(IHttpClient):
            def get(self, url: str, timeout: int = 30) -> str:
                super().get(url, timeout)
                return "test"
        
        client = PassTestClient()
        response = client.get("https://example.com")
        self.assertEqual(response, "test")
    
    def test_iurl_builder_pass_statement_coverage(self):
        
        class PassTestBuilder(IUrlBuilder):
            def build_search_url(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> str:
                super().build_search_url(keyword, sort_by_price, page)
                return "test"
        
        builder = PassTestBuilder()
        url = builder.build_search_url("test")
        self.assertEqual(url, "test")
    
    def test_ihtml_parser_pass_statement_coverage(self):
        
        class PassTestParser(IHtmlParser):
            def parse_products(self, html_content: str) -> list:
                super().parse_products(html_content)
                return []
        
        parser = PassTestParser()
        products = parser.parse_products("test")
        self.assertEqual(products, [])
    
    def test_iprice_scraper_pass_statement_coverage(self):
        
        class PassTestScraper(IPriceScraper):
            def scrape_products(self, keyword: str, sort_by_price: bool = True, page: int = 0) -> ScrapingResult:
                super().scrape_products(keyword, sort_by_price, page)
                return ScrapingResult(products=[], success=True)
        
        scraper = PassTestScraper()
        result = scraper.scrape_products("test")
        self.assertTrue(result.success)