from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock


class TestGovernmentWageDataModel(TestCase):    
    def test_item_creation_with_defaults(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        item = GovernmentWageItem(
            item_number="1",
            work_code="6.1.1",
            work_description="Mandor",
            unit="OH",
            unit_price_idr=150000,
            region="Kab. Cilacap"
        )
        
        self.assertEqual(item.work_code, "6.1.1")
        self.assertEqual(item.year, "2025")
        self.assertEqual(item.edition, "Edisi Ke - 2")
    
    def test_item_with_custom_metadata(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        item = GovernmentWageItem(
            item_number="2",
            work_code="6.1.2",
            work_description="Kepala Tukang",
            unit="OH",
            unit_price_idr=130000,
            region="Kota Semarang",
            year="2026",
            edition="Edisi Ke - 3"
        )
        
        self.assertEqual(item.year, "2026")
        self.assertEqual(item.edition, "Edisi Ke - 3")


class TestGovernmentWageScraper(TestCase):    
    def setUp(self):
        from api.government_wage.scraper import GovernmentWageScraper
        
        self.mock_http_client = Mock()
        self.mock_url_builder = Mock()
        self.mock_html_parser = Mock()
        
        self.scraper = GovernmentWageScraper(
            self.mock_http_client,
            self.mock_url_builder,
            self.mock_html_parser
        )
    
    def test_scrape_region_data_success(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        
        mock_item = GovernmentWageItem(
            item_number="1",
            work_code="6.1.1",
            work_description="Mandor",
            unit="OH",
            unit_price_idr=150000,
            region="Kab. Cilacap"
        )
        
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[mock_item])
        
        result = self.scraper.scrape_region_data("Kab. Cilacap")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].work_code, "6.1.1")
    
    def test_scrape_region_with_default_region(self):
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[])
        
        result = self.scraper.scrape_region_data(None)
        
        self.assertIsInstance(result, list)
    
    def test_scrape_region_sets_client_attributes(self):
        self.mock_http_client.region_label = None
        self.mock_http_client.auto_select_region = None
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[])
        
        self.scraper.scrape_region_data("Kab. Semarang")
        
        self.assertEqual(self.mock_http_client.region_label, "Kab. Semarang")
        self.assertTrue(self.mock_http_client.auto_select_region)
    
    def test_scrape_region_exception_handling(self):
        self.mock_url_builder.build_search_url.side_effect = Exception("Test error")
        
        result = self.scraper.scrape_region_data("Kab. Cilacap")
        
        self.assertEqual(result, [])
    
    def test_scrape_all_regions_success(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        
        mock_item = GovernmentWageItem(
            item_number="1",
            work_code="6.1.1",
            work_description="Mandor",
            unit="OH",
            unit_price_idr=150000,
            region="Kab. Cilacap"
        )
        
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[mock_item])
        
        with patch('time.sleep'):
            result = self.scraper.scrape_all_regions(max_regions=2)
        
        self.assertGreater(len(result), 0)
    
    def test_scrape_all_regions_continues_on_error(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        
        self.mock_http_client.get.side_effect = [
            "<html>test</html>",
            Exception("Network error")
        ]
        
        mock_item = GovernmentWageItem(
            item_number="1",
            work_code="6.1.1",
            work_description="Mandor",
            unit="OH",
            unit_price_idr=150000,
            region="Kab. Cilacap"
        )
        
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[mock_item])
        
        with patch('time.sleep'):
            result = self.scraper.scrape_all_regions(max_regions=2)
        
        self.assertEqual(len(result), 1)
    
    def test_search_by_work_code_with_region(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        
        mock_item = GovernmentWageItem(
            item_number="1",
            work_code="6.1.1",
            work_description="Mandor",
            unit="OH",
            unit_price_idr=150000,
            region="Kab. Semarang"
        )
        
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[mock_item])
        
        result = self.scraper.search_by_work_code("6.1.1", region="Kab. Semarang")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].work_code, "6.1.1")
    
    def test_search_by_work_code_without_region(self):
        from api.government_wage.scraper import GovernmentWageItem
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        
        mock_item = GovernmentWageItem(
            item_number="1",
            work_code="6.1.1",
            work_description="Mandor",
            unit="OH",
            unit_price_idr=150000,
            region="Kab. Cilacap"
        )
        
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[mock_item])
        
        result = self.scraper.search_by_work_code("6.1.1")
        
        self.assertEqual(len(result), 1)
    
    def test_search_by_work_code_exception_handling(self):
        self.mock_url_builder.build_search_url.side_effect = Exception("Test error")
        
        result = self.scraper.search_by_work_code("6.1.1")
        
        self.assertEqual(result, [])
    
    def test_search_in_region_sets_search_keyword(self):
        self.mock_http_client.search_keyword = None
        self.mock_http_client.region_label = None
        self.mock_http_client.auto_select_region = None
        
        self.mock_url_builder.build_search_url.return_value = "http://test.com"
        self.mock_http_client.get.return_value = "<html>test</html>"
        self.mock_html_parser.parse_government_wage_data = Mock(return_value=[])
        
        self.scraper._search_in_region("6.1.1", "Kab. Semarang")
        
        self.assertEqual(self.mock_http_client.search_keyword, "6.1.1")
        self.assertEqual(self.mock_http_client.region_label, "Kab. Semarang")
    
    def test_get_available_regions(self):
        regions = self.scraper.get_available_regions()
        
        self.assertIsInstance(regions, list)
        self.assertGreater(len(regions), 0)
        self.assertIn("Kab. Cilacap", regions)
    
    def test_context_manager_usage(self):
        from api.government_wage.scraper import GovernmentWageScraper
        
        mock_client = MagicMock()
        scraper = GovernmentWageScraper(mock_client, self.mock_url_builder, self.mock_html_parser)
        
        # Test that context manager enters and exits without errors
        with scraper:
            # Verify the scraper is usable within context
            self.assertIsNotNone(scraper)
        
        # If we reach here, context manager worked correctly
    
    def test_create_scraper_factory(self):
        from api.government_wage.scraper import create_government_wage_scraper, GovernmentWageScraper
        
        with patch('api.government_wage.scraper.GovernmentWagePlaywrightClient'), \
             patch('api.government_wage.scraper.GovernmentWageUrlBuilder'), \
             patch('api.government_wage.scraper.GovernmentWageHtmlParser'):
            
            scraper = create_government_wage_scraper(headless=True, browser_type="chromium")
            
            self.assertIsInstance(scraper, GovernmentWageScraper)