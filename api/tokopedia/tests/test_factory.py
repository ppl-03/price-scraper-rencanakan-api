import unittest
from django.test import TestCase

from api.tokopedia.factory import create_tokopedia_scraper
from api.tokopedia.scraper import TokopediaPriceScraper
from api.tokopedia.url_builder import TokopediaUrlBuilder
from api.tokopedia.html_parser import TokopediaHtmlParser
from api.tokopedia_core import BaseHttpClient


class TestTokopediaFactory(TestCase):
    """Test factory function for creating Tokopedia scraper"""
    
    def test_create_tokopedia_scraper(self):
        """Test that factory creates a properly configured scraper"""
        scraper = create_tokopedia_scraper()
        
        # Verify the scraper is created
        self.assertIsNotNone(scraper)
        self.assertIsInstance(scraper, TokopediaPriceScraper)
        
        # Verify components are properly initialized
        self.assertIsInstance(scraper.http_client, BaseHttpClient)
        self.assertIsInstance(scraper.url_builder, TokopediaUrlBuilder)
        self.assertIsInstance(scraper.html_parser, TokopediaHtmlParser)
    
    def test_create_tokopedia_scraper_returns_different_instances(self):
        """Test that factory creates new instances on each call"""
        scraper1 = create_tokopedia_scraper()
        scraper2 = create_tokopedia_scraper()
        
        # Should be different instances
        self.assertIsNot(scraper1, scraper2)
        self.assertIsNot(scraper1.http_client, scraper2.http_client)
        self.assertIsNot(scraper1.url_builder, scraper2.url_builder)
        self.assertIsNot(scraper1.html_parser, scraper2.html_parser)


if __name__ == '__main__':
    unittest.main()
