import unittest
from api.depobangunan.url_builder import DepoUrlBuilder
from api.interfaces import UrlBuilderError


class TestDepoUrlBuilder(unittest.TestCase):
    
    def setUp(self):
        self.url_builder = DepoUrlBuilder()
    
    def test_build_search_url_basic(self):
        url = self.url_builder.build_search_url("cat")
        expected = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        self.assertEqual(url, expected)
    
    def test_build_search_url_with_sort_false(self):
        url = self.url_builder.build_search_url("cat", sort_by_price=False)
        expected = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat"
        self.assertEqual(url, expected)
    
    def test_build_search_url_with_sort_true(self):
        url = self.url_builder.build_search_url("cat", sort_by_price=True)
        expected = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        self.assertEqual(url, expected)
    
    def test_build_search_url_with_special_characters(self):
        url = self.url_builder.build_search_url("cat tembok")
        expected = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat+tembok&product_list_order=low_to_high"
        self.assertEqual(url, expected)
    
    def test_build_search_url_empty_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError):
            self.url_builder.build_search_url("")
    
    def test_build_search_url_whitespace_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError):
            self.url_builder.build_search_url("   ")
    
    def test_build_search_url_none_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError):
            self.url_builder.build_search_url(None)
    
    def test_build_search_url_with_page_parameter(self):
        url = self.url_builder.build_search_url("cat", page=1)
        expected = "https://www.depobangunan.co.id/catalogsearch/result/?q=cat&product_list_order=low_to_high"
        self.assertEqual(url, expected)
    
    def test_build_search_url_with_custom_base_url(self):
        custom_builder = DepoUrlBuilder(
            base_url="https://custom.depobangunan.co.id",
            search_path="/search/"
        )
        url = custom_builder.build_search_url("cat")
        expected = "https://custom.depobangunan.co.id/search/?q=cat&product_list_order=low_to_high"
        self.assertEqual(url, expected)


if __name__ == '__main__':
    unittest.main()