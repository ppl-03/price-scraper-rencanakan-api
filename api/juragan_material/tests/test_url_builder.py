from unittest import TestCase
from unittest.mock import patch
from api.interfaces import UrlBuilderError
from api.juragan_material.url_builder import JuraganMaterialUrlBuilder


class TestJuraganMaterialUrlBuilder(TestCase):
    """Test cases for JuraganMaterialUrlBuilder."""
    
    def setUp(self):
        self.url_builder = JuraganMaterialUrlBuilder()
    
    def test_basic_url_building(self):
        """Test basic URL building functionality."""
        url = self.url_builder.build_search_url("semen")
        self.assertIn("juraganmaterial.id", url)
        self.assertIn("keyword=semen", url)
        self.assertIn("sort=lowest_price", url)
        self.assertIn("page=1", url)
    
    def test_url_building_with_pagination(self):
        """Test URL building with pagination."""
        url = self.url_builder.build_search_url("semen", page=3)
        self.assertIn("page=4", url)  # JuraganMaterial uses 1-based pagination
        self.assertIn("keyword=semen", url)
    
    def test_url_building_without_sorting(self):
        """Test URL building without price sorting."""
        url = self.url_builder.build_search_url("semen", sort_by_price=False)
        self.assertIn("keyword=semen", url)
        self.assertIn("sort=relevance", url)
    
    def test_keyword_trimming(self):
        """Test that keywords are properly trimmed."""
        url = self.url_builder.build_search_url("  semen  ")
        self.assertIn("keyword=semen", url)
        self.assertNotIn("keyword=%20%20semen%20%20", url)
    
    def test_empty_keyword_raises_error(self):
        """Test that empty keyword raises error."""
        with self.assertRaises(UrlBuilderError) as context:
            self.url_builder.build_search_url("")
        self.assertIn("Keyword cannot be empty", str(context.exception))
    
    def test_whitespace_only_keyword_raises_error(self):
        """Test that whitespace-only keyword raises error."""
        with self.assertRaises(UrlBuilderError) as context:
            self.url_builder.build_search_url("   ")
        self.assertIn("Keyword cannot be empty", str(context.exception))
    
    def test_negative_page_raises_error(self):
        """Test that negative page number raises error."""
        with self.assertRaises(UrlBuilderError) as context:
            self.url_builder.build_search_url("semen", page=-1)
        self.assertIn("Page number cannot be negative", str(context.exception))