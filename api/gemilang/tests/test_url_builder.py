from unittest import TestCase
from unittest.mock import patch
from api.interfaces import UrlBuilderError
from api.gemilang.url_builder import GemilangUrlBuilder
class TestGemilangUrlBuilder(TestCase):
    def setUp(self):
        self.url_builder = GemilangUrlBuilder()
    def test_basic_url_building(self):
        url = self.url_builder.build_search_url("cat")
        self.assertIn("gemilang-store.com", url)
        self.assertIn("keyword=cat", url)
        self.assertIn("sort=price_asc", url)
        self.assertIn("page=0", url)
    def test_url_building_with_pagination(self):
        url = self.url_builder.build_search_url("cat", page=3)
        self.assertIn("page=3", url)
        self.assertIn("keyword=cat", url)
    def test_url_building_without_sorting(self):
        url = self.url_builder.build_search_url("cat", sort_by_price=False)
        self.assertIn("keyword=cat", url)
        self.assertNotIn("sort=price_asc", url)
    def test_keyword_trimming(self):
        url = self.url_builder.build_search_url("  cat  ")
        self.assertIn("keyword=cat", url)
        self.assertNotIn("keyword=%20%20cat%20%20", url)
        self.assertIn("sort=price_asc", url)
        self.assertIn("page=0", url)
    def test_custom_base_url_and_path(self):
        custom_builder = GemilangUrlBuilder(
            base_url="https://custom-gemilang.com",
            search_path="/custom/search"
        )
        url = custom_builder.build_search_url("test")
        self.assertIn("custom-gemilang.com", url)
        self.assertIn("/custom/search", url)
    def test_empty_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError) as context:
            self.url_builder.build_search_url("")
        self.assertIn("Keyword cannot be empty", str(context.exception))
    def test_whitespace_only_keyword_raises_error(self):
        with self.assertRaises(UrlBuilderError) as context:
            self.url_builder.build_search_url("   ")
        self.assertIn("Keyword cannot be empty", str(context.exception))
    def test_negative_page_raises_error(self):
        with self.assertRaises(UrlBuilderError) as context:
            self.url_builder.build_search_url("cat", page=-1)
        self.assertIn("Page number cannot be negative", str(context.exception))
    def test_zero_page_is_valid(self):
        url = self.url_builder.build_search_url("cat", page=0)
        self.assertIn("page=0", url)
    def test_large_page_number(self):
        url = self.url_builder.build_search_url("cat", page=999)
        self.assertIn("page=999", url)
    def test_special_characters_in_keyword(self):
        url = self.url_builder.build_search_url("cat & dog")
        self.assertIn("keyword=", url)
        self.assertTrue(any(char in url for char in ["cat", "dog"]))
    def test_gemilang_specific_params(self):
        url = self.url_builder.build_search_url("test", sort_by_price=True)
        self.assertIn("sort=price_asc", url)
    @patch('api.gemilang.url_builder.config')
    def test_uses_config_defaults(self, mock_config):
        mock_config.gemilang_base_url = "https://test-gemilang.com"
        mock_config.gemilang_search_path = "/test/search"
        builder = GemilangUrlBuilder()
        url = builder.build_search_url("test")
        self.assertIn("test-gemilang.com", url)
        self.assertIn("/test/search", url)
