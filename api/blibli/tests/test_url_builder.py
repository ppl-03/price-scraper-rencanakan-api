from unittest import TestCase
from unittest.mock import patch
from api.interfaces import UrlBuilderError
from api.blibli.url_builder import BlibliUrlBuilder

class TestBlibliUrlBuilder(TestCase):
    def setUp(self):
        self.url_builder = BlibliUrlBuilder()

    def test_basic_url_building(self):
        url = self.url_builder.build_search_url("cat")
        self.assertIn("blibli.com/cari/cat", url)
        # Category parameter removed to make searches less restrictive
        # self.assertIn("category=BA-1000038", url)
        self.assertIn("sort=3", url)
        self.assertIn("page=1", url)
        self.assertIn("start=0", url)

    def test_url_building_with_pagination(self):
        url = self.url_builder.build_search_url("cat", page=2)
        self.assertIn("page=3", url)  # 1-based page index
        self.assertIn("start=80", url)  # 2*40

    def test_url_building_without_sorting(self):
        url = self.url_builder.build_search_url("cat", sort_by_price=False)
        self.assertIn("sort=0", url)

    def test_keyword_trimming(self):
        url = self.url_builder.build_search_url("  cat  ")
        self.assertIn("/cari/cat?", url)
        self.assertNotIn("/cari/%20%20cat%20%20?", url)

    def test_special_characters_in_keyword(self):
        url = self.url_builder.build_search_url("cat & dog")
        self.assertIn("/cari/cat%20%26%20dog?", url)

    def test_empty_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError):
            self.url_builder.build_search_url("")

    def test_whitespace_only_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError):
            self.url_builder.build_search_url("   ")

    def test_negative_page_raises_error(self):
        with self.assertRaises(UrlBuilderError):
            self.url_builder.build_search_url("cat", page=-1)

    @patch('api.blibli.url_builder.config')
    def test_uses_config_defaults(self, mock_config):
        mock_config.blibli_base_url = "https://test-blibli.com"
        mock_config.blibli_search_path = "/test/search/"
        builder = BlibliUrlBuilder()
        url = builder.build_search_url("test")
        self.assertIn("test-blibli.com", url)
        self.assertIn("/test/search/test?", url)
        
    def test_unicode_keyword(self):
        url = self.url_builder.build_search_url("kayu üñîçødë")
        self.assertIn("/cari/kayu%20%C3%BC%C3%B1%C3%AE%C3%A7%C3%B8d%C3%AB?", url)
        
    def test_custom_base_url_and_search_path(self):
        builder = BlibliUrlBuilder(base_url="https://custom.com", search_path="/find/")
        url = builder.build_search_url("cat")
        self.assertIn("custom.com/find/cat?", url)
    
    def test_sort_parameter_mapping(self):
        url_cheapest = self.url_builder.build_search_url("cat", sort_by_price=True)
        url_default = self.url_builder.build_search_url("cat", sort_by_price=False)
        self.assertIn("sort=3", url_cheapest)
        self.assertIn("sort=0", url_default)
    
    def test_search_path_trailing_slash(self):
        builder = BlibliUrlBuilder(search_path="/cari")
        url = builder.build_search_url("cat")
        self.assertIn("/cari/cat?", url)