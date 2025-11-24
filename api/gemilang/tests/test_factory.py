"""Tests for gemilang factory functions"""
from django.test import TestCase
from api.gemilang.factory import create_gemilang_location_scraper_simple
from api.gemilang.location_scraper import GemilangLocationScraper


class TestGemilangFactory(TestCase):
    def test_create_gemilang_location_scraper_simple(self):
        """Test lines 48-51: create_gemilang_location_scraper_simple function"""
        scraper = create_gemilang_location_scraper_simple()
        
        self.assertIsInstance(scraper, GemilangLocationScraper)
        # Verify it's a functional scraper
        self.assertTrue(hasattr(scraper, 'scrape_locations'))
