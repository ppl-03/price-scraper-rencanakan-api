import unittest
from unittest.mock import patch, MagicMock
from api.mitra10.factory import create_mitra10_scraper, create_mitra10_location_scraper
from api.mitra10.scraper import Mitra10PriceScraper
from api.mitra10.location_scraper import Mitra10LocationScraper


class TestMitra10Factory(unittest.TestCase):

    @patch('api.mitra10.factory.BatchPlaywrightClient')
    @patch('api.mitra10.factory.Mitra10UrlBuilder')
    @patch('api.mitra10.factory.Mitra10HtmlParser')
    def test_create_mitra10_scraper(self, mock_html_parser, mock_url_builder, mock_batch_client):
        """Test creation of Mitra10 price scraper"""
        mock_url_builder_instance = MagicMock()
        mock_html_parser_instance = MagicMock()
        
        mock_url_builder.return_value = mock_url_builder_instance
        mock_html_parser.return_value = mock_html_parser_instance
        
        scraper = create_mitra10_scraper()
        
        self.assertIsInstance(scraper, Mitra10PriceScraper)
        mock_url_builder.assert_called_once()
        mock_html_parser.assert_called_once()
    
    def test_create_mitra10_location_scraper(self):
        """Test creation of Mitra10 location scraper"""
        scraper = create_mitra10_location_scraper()
        
        self.assertIsInstance(scraper, Mitra10LocationScraper)

    def test_factory_functions_exist(self):
        """Test that factory functions exist and are callable"""
        self.assertTrue(callable(create_mitra10_scraper))
        self.assertTrue(callable(create_mitra10_location_scraper))