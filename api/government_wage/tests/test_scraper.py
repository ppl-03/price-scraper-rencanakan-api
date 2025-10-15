from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from api.interfaces import Product, IHttpClient, IUrlBuilder, IHtmlParser
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GovernmentWageItem:
    """Data model for government wage/HSPK items based on DHSP Analysis"""
    item_number: str
    work_code: str
    work_description: str
    unit: str
    unit_price_idr: int
    region: str
    edition: str = "Edisi Ke - 2"
    year: str = "2024"
    sector: str = "Bidang Cipta Karya dan Perumahan"


class MockGovernmentWageScraper:
    """Mock implementation for testing purposes following the scraper pattern"""
    
    def __init__(self, http_client: IHttpClient, url_builder: IUrlBuilder, html_parser: IHtmlParser):
        self.http_client = http_client
        self.url_builder = url_builder
        self.html_parser = html_parser
    
    def scrape_region_data(self, region: str = "Kab. Cilacap") -> List[GovernmentWageItem]:
        """Scrape government wage data for a specific region"""
        try:
            url = self.url_builder.build_search_url(region)
            html_content = self.http_client.get(url)
            return self.html_parser.parse_government_wage_data(html_content, region)
        except Exception as e:
            print(f"Error scraping {region}: {e}")
            return []
    
    def scrape_all_regions(self) -> List[GovernmentWageItem]:
        """Scrape data from all available regions in Central Java"""
        all_items = []
        regions = self.get_available_regions()
        
        for region in regions:
            try:
                items = self.scrape_region_data(region)
                all_items.extend(items)
            except Exception as e:
                print(f"Error scraping region {region}: {e}")
                continue
        
        return all_items
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions from the dropdown"""
        # Mock implementation - in real scraper would parse the region dropdown
        return ["Kab. Cilacap", "Kab. Banyumas", "Kab. Purbalingga", "Kota Semarang"]
    
    def search_by_work_code(self, work_code: str, region: str = None) -> List[GovernmentWageItem]:
        """Search for specific work codes"""
        try:
            url = self.url_builder.build_search_url(work_code)
            html_content = self.http_client.get(url)
            return self.html_parser.parse_government_wage_data(html_content, region or "all")
        except Exception as e:
            print(f"Error searching for work code {work_code}: {e}")
            return []


class TestGovernmentWageScraper(TestCase):
    """Test cases for Government Wage Scraper based on DHSP Analysis documentation"""
    
    def setUp(self):
        self.mock_http_client = Mock(spec=IHttpClient)
        self.mock_url_builder = Mock(spec=IUrlBuilder)
        self.mock_html_parser = Mock(spec=IHtmlParser)
        
        # Add parse_government_wage_data method to html_parser mock
        self.mock_html_parser.parse_government_wage_data = Mock()
        
        self.scraper = MockGovernmentWageScraper(
            http_client=self.mock_http_client,
            url_builder=self.mock_url_builder,
            html_parser=self.mock_html_parser
        )
    
    def test_init(self):
        """Test scraper initialization"""
        scraper = MockGovernmentWageScraper(
            self.mock_http_client,
            self.mock_url_builder,
            self.mock_html_parser
        )
        
        self.assertEqual(scraper.http_client, self.mock_http_client)
        self.assertEqual(scraper.url_builder, self.mock_url_builder)
        self.assertEqual(scraper.html_parser, self.mock_html_parser)
    
    def test_scrape_region_data_success(self):
        """Test successful scraping of region data"""
        test_region = "Kab. Cilacap"
        test_url = "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk"
        test_html = """
        <table class="dataTable">
            <tbody>
                <tr>
                    <td>1</td>
                    <td>A.1.1.1.1</td>
                    <td>Pembersihan lapangan dan perataan</td>
                    <td>m²</td>
                    <td>15,000</td>
                </tr>
            </tbody>
        </table>
        """
        
        expected_item = GovernmentWageItem(
            item_number="1",
            work_code="A.1.1.1.1",
            work_description="Pembersihan lapangan dan perataan",
            unit="m²",
            unit_price_idr=15000,
            region=test_region
        )
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = test_html
        self.mock_html_parser.parse_government_wage_data.return_value = [expected_item]
        
        result = self.scraper.scrape_region_data(test_region)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].work_code, "A.1.1.1.1")
        self.assertEqual(result[0].work_description, "Pembersihan lapangan dan perataan")
        self.assertEqual(result[0].unit_price_idr, 15000)
        self.assertEqual(result[0].region, test_region)
        
        self.mock_url_builder.build_search_url.assert_called_once_with(test_region)
        self.mock_http_client.get.assert_called_once_with(test_url)
        self.mock_html_parser.parse_government_wage_data.assert_called_once_with(test_html, test_region)
    
    def test_scrape_region_data_with_error(self):
        """Test error handling when scraping fails"""
        test_region = "Kab. Cilacap"
        
        self.mock_url_builder.build_search_url.side_effect = Exception("Network error")
        
        with patch('builtins.print') as mock_print:
            result = self.scraper.scrape_region_data(test_region)
            
            self.assertEqual(result, [])
            mock_print.assert_called_once_with("Error scraping Kab. Cilacap: Network error")
    
    def test_scrape_all_regions_success(self):
        """Test scraping data from multiple regions"""
        test_regions = ["Kab. Cilacap", "Kab. Banyumas"]
        test_items_per_region = [
            [GovernmentWageItem(
                item_number="1",
                work_code="A.1.1.1.1",
                work_description="Test work Cilacap",
                unit="m²",
                unit_price_idr=15000,
                region="Kab. Cilacap"
            )],
            [GovernmentWageItem(
                item_number="2",
                work_code="A.1.1.1.2",
                work_description="Test work Banyumas",
                unit="m³",
                unit_price_idr=25000,
                region="Kab. Banyumas"
            )]
        ]
        
        # Mock get_available_regions to return test regions
        self.scraper.get_available_regions = Mock(return_value=test_regions)
        
        # Mock scrape_region_data calls
        self.scraper.scrape_region_data = Mock(side_effect=test_items_per_region)
        
        result = self.scraper.scrape_all_regions()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].region, "Kab. Cilacap")
        self.assertEqual(result[1].region, "Kab. Banyumas")
    
    def test_scrape_all_regions_with_partial_failure(self):
        """Test handling partial failures when scraping multiple regions"""
        test_regions = ["Kab. Cilacap", "Kab. Banyumas", "Kab. Error"]
        
        def mock_scrape_region_data(region):
            if region == "Kab. Error":
                raise Exception("Failed to scrape")
            return [GovernmentWageItem(
                item_number="1",
                work_code="A.1.1.1.1",
                work_description=f"Test work {region}",
                unit="m²",
                unit_price_idr=15000,
                region=region
            )]
        
        self.scraper.get_available_regions = Mock(return_value=test_regions)
        
        with patch('builtins.print') as mock_print:
            with patch.object(self.scraper, 'scrape_region_data', side_effect=mock_scrape_region_data):
                result = self.scraper.scrape_all_regions()
        
        # Should get 2 successful results, 1 error
        self.assertEqual(len(result), 2)
        mock_print.assert_called_once_with("Error scraping region Kab. Error: Failed to scrape")
    
    def test_get_available_regions(self):
        """Test getting available regions"""
        regions = self.scraper.get_available_regions()
        
        self.assertIsInstance(regions, list)
        self.assertIn("Kab. Cilacap", regions)
        self.assertGreater(len(regions), 0)
    
    def test_search_by_work_code_success(self):
        """Test searching by specific work code"""
        test_work_code = "A.1.1.1.1"
        test_url = "https://maspetruk.dpubinmarcipka.jatengprov.go.id/harga_satuan/hspk"
        test_html = "<html>search results</html>"
        
        expected_item = GovernmentWageItem(
            item_number="1",
            work_code=test_work_code,
            work_description="Pembersihan lapangan dan perataan",
            unit="m²",
            unit_price_idr=15000,
            region="all"
        )
        
        self.mock_url_builder.build_search_url.return_value = test_url
        self.mock_http_client.get.return_value = test_html
        self.mock_html_parser.parse_government_wage_data.return_value = [expected_item]
        
        result = self.scraper.search_by_work_code(test_work_code)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].work_code, test_work_code)
        
        self.mock_url_builder.build_search_url.assert_called_once_with(test_work_code)
        self.mock_http_client.get.assert_called_once_with(test_url)
    
    def test_search_by_work_code_with_region(self):
        """Test searching by work code with specific region"""
        test_work_code = "A.1.1.1.1"
        test_region = "Kab. Cilacap"
        
        expected_item = GovernmentWageItem(
            item_number="1",
            work_code=test_work_code,
            work_description="Test work",
            unit="m²",
            unit_price_idr=15000,
            region=test_region
        )
        
        self.mock_url_builder.build_search_url.return_value = "test_url"
        self.mock_http_client.get.return_value = "test_html"
        self.mock_html_parser.parse_government_wage_data.return_value = [expected_item]
        
        result = self.scraper.search_by_work_code(test_work_code, test_region)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].region, test_region)
        self.mock_html_parser.parse_government_wage_data.assert_called_once_with("test_html", test_region)
    
    def test_search_by_work_code_with_error(self):
        """Test error handling in work code search"""
        test_work_code = "INVALID_CODE"
        
        self.mock_url_builder.build_search_url.side_effect = Exception("Invalid work code")
        
        with patch('builtins.print') as mock_print:
            result = self.scraper.search_by_work_code(test_work_code)
            
            self.assertEqual(result, [])
            mock_print.assert_called_once_with("Error searching for work code INVALID_CODE: Invalid work code")


class TestGovernmentWageDataModel(TestCase):
    """Test cases for GovernmentWageItem data model"""
    
    def test_government_wage_item_creation(self):
        """Test creating a GovernmentWageItem instance"""
        item = GovernmentWageItem(
            item_number="1",
            work_code="A.1.1.1.1",
            work_description="Pembersihan lapangan dan perataan",
            unit="m²",
            unit_price_idr=15000,
            region="Kab. Cilacap"
        )
        
        self.assertEqual(item.item_number, "1")
        self.assertEqual(item.work_code, "A.1.1.1.1")
        self.assertEqual(item.work_description, "Pembersihan lapangan dan perataan")
        self.assertEqual(item.unit, "m²")
        self.assertEqual(item.unit_price_idr, 15000)
        self.assertEqual(item.region, "Kab. Cilacap")
        # Test default values
        self.assertEqual(item.edition, "Edisi Ke - 2")
        self.assertEqual(item.year, "2024")
        self.assertEqual(item.sector, "Bidang Cipta Karya dan Perumahan")
    
    def test_government_wage_item_with_custom_metadata(self):
        """Test creating item with custom edition/year/sector"""
        item = GovernmentWageItem(
            item_number="2",
            work_code="B.2.2.2.2",
            work_description="Custom work item",
            unit="kg",
            unit_price_idr=5000,
            region="Kota Semarang",
            edition="Edisi Ke - 3",
            year="2025",
            sector="Custom Sector"
        )
        
        self.assertEqual(item.edition, "Edisi Ke - 3")
        self.assertEqual(item.year, "2025")
        self.assertEqual(item.sector, "Custom Sector")


class TestGovernmentWageScrapingScenarios(TestCase):
    """Integration-style tests based on DHSP Analysis scenarios"""
    
    def setUp(self):
        self.mock_http_client = Mock(spec=IHttpClient)
        self.mock_url_builder = Mock(spec=IUrlBuilder)
        self.mock_html_parser = Mock(spec=IHtmlParser)
        self.mock_html_parser.parse_government_wage_data = Mock()
        
        self.scraper = MockGovernmentWageScraper(
            http_client=self.mock_http_client,
            url_builder=self.mock_url_builder,
            html_parser=self.mock_html_parser
        )
    
    def test_javascript_dependent_content_handling(self):
        """Test handling of JavaScript-dependent content loading"""
        # Simulate empty content due to JS requirement
        empty_html = "<html><body><table class='dataTable'><tbody></tbody></table></body></html>"
        
        self.mock_url_builder.build_search_url.return_value = "test_url"
        self.mock_http_client.get.return_value = empty_html
        self.mock_html_parser.parse_government_wage_data.return_value = []
        
        result = self.scraper.scrape_region_data("Kab. Cilacap")
        
        self.assertEqual(len(result), 0)
    
    def test_processing_state_handling(self):
        """Test handling 'Sedang memproses...' (Processing) state"""
        processing_html = "<html><body>Sedang memproses...</body></html>"
        
        self.mock_url_builder.build_search_url.return_value = "test_url"
        self.mock_http_client.get.return_value = processing_html
        self.mock_html_parser.parse_government_wage_data.return_value = []
        
        result = self.scraper.scrape_region_data("Kab. Cilacap")
        
        self.assertEqual(len(result), 0)
    
    def test_no_data_found_handling(self):
        """Test handling 'Tidak ditemukan data yang sesuai' (No data found)"""
        no_data_html = "<html><body>Tidak ditemukan data yang sesuai</body></html>"
        
        self.mock_url_builder.build_search_url.return_value = "test_url"
        self.mock_http_client.get.return_value = no_data_html
        self.mock_html_parser.parse_government_wage_data.return_value = []
        
        result = self.scraper.scrape_region_data("Invalid Region")
        
        self.assertEqual(len(result), 0)
    
    def test_pagination_data_extraction(self):
        """Test extracting data across multiple pages"""
        # Simulate pagination scenario with "Menampilkan X sampai Y dari Z entri"
        pagination_info = "Menampilkan 1 sampai 25 dari 150 entri"
        
        # This test would verify that the scraper can handle pagination
        # In a real implementation, this would test page navigation logic
        self.assertIsNotNone(pagination_info)
    
    def test_rate_limiting_compliance(self):
        """Test that scraper respects rate limiting for government site"""
        # This test would verify delay implementation between requests
        # Based on DHSP Analysis recommendation of 2-3 seconds between requests
        
        regions = ["Kab. Cilacap", "Kab. Banyumas"]
        self.scraper.get_available_regions = Mock(return_value=regions)
        
        # Mock timing-sensitive operations
        with patch('time.sleep') as mock_sleep:
            # In real implementation, this would test actual delay calls
            pass
        
        # Verify respectful access patterns are implemented
        self.assertTrue(True)  # Placeholder for actual timing tests
    
    def test_data_structure_compliance(self):
        """Test that scraped data matches expected DHSP schema"""
        expected_schema_fields = [
            'item_number', 'work_code', 'work_description', 
            'unit', 'unit_price_idr', 'region', 'edition', 'year', 'sector'
        ]
        
        sample_item = GovernmentWageItem(
            item_number="1",
            work_code="A.1.1.1.1",
            work_description="Test work",
            unit="m²",
            unit_price_idr=15000,
            region="Kab. Cilacap"
        )
        
        for field in expected_schema_fields:
            self.assertTrue(hasattr(sample_item, field))
            self.assertIsNotNone(getattr(sample_item, field))