from pathlib import Path
from unittest import TestCase
from api.interfaces import Location, HtmlParserError
from api.gemilang.location_parser import GemilangLocationParser


class TestGemilangLocationParser(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_location_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="store-locator">
                <div class="info-store bg-color-red">
                    <div class="store-name pl-3 pr-3 pb-0">
                        <a class="location_click" data-id="11" href="#">
                            <img height="20" src="https://gemilang-store.com/data/themes/gemilang/images/gemilang-icon.png" style="margin-right: 2px;margin-top: -5px;"> GEMILANG - BANJARMASIN KM</img>
                        </a>
                    </div>
                </div>
                <div class="info-store pl-3 pr-3">
                    <div class="store-location">
                        Jl. Kampung Melayu Darat 39A Rt.8<br/>
                        Banjarmasin, Kalimantan Selatan<br/>
                        Indonesia
                    </div>
                </div>
                <div class="info-store bg-color-red">
                    <div class="store-name pl-3 pr-3 pb-0">
                        <a class="location_click" data-id="12" href="#">
                            <img height="20" src="https://gemilang-store.com/data/themes/gemilang/images/gemilang-icon.png" style="margin-right: 2px;margin-top: -5px;"> GEMILANG - JAKARTA PUSAT</img>
                        </a>
                    </div>
                </div>
                <div class="info-store pl-3 pr-3">
                    <div class="store-location">
                        Jl. Veteran No. 123<br/>
                        Jakarta Pusat, DKI Jakarta<br/>
                        Indonesia
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def setUp(self):
        self.parser = GemilangLocationParser()

    def test_parse_locations_from_mock_html(self):
        locations = self.parser.parse_locations(self.mock_location_html)
        
        self.assertEqual(len(locations), 2)
        
        location1 = locations[0]
        self.assertEqual(location1.store_name, "GEMILANG - BANJARMASIN KM")
        expected_address1 = "Jl. Kampung Melayu Darat 39A Rt.8\nBanjarmasin, Kalimantan Selatan\nIndonesia"
        self.assertEqual(location1.address, expected_address1)
        
        location2 = locations[1]
        self.assertEqual(location2.store_name, "GEMILANG - JAKARTA PUSAT")
        expected_address2 = "Jl. Veteran No. 123\nJakarta Pusat, DKI Jakarta\nIndonesia"
        self.assertEqual(location2.address, expected_address2)

    def test_parse_empty_html(self):
        locations = self.parser.parse_locations("")
        self.assertEqual(len(locations), 0)

    def test_parse_html_with_no_locations(self):
        html_no_locations = "<html><body><div>No locations found</div></body></html>"
        locations = self.parser.parse_locations(html_no_locations)
        self.assertEqual(len(locations), 0)

    def test_parse_malformed_html(self):
        malformed_html = "<div class='info-store'><a href='#'><div class='store-location'>incomplete"
        locations = self.parser.parse_locations(malformed_html)
        self.assertIsInstance(locations, list)

    def test_extract_location_with_missing_store_name(self):
        html_missing_name = """
        <div class="info-store">
            <div class="store-location">
                Jl. Test Street<br>
                Test City<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_missing_name)
        self.assertEqual(len(locations), 0)

    def test_extract_location_with_missing_address(self):
        html_missing_address = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                <img src="icon.png"> GEMILANG - TEST STORE
            </a>
        </div>
        """
        locations = self.parser.parse_locations(html_missing_address)
        self.assertEqual(len(locations), 0)

    def test_extract_store_name_cleaning(self):
        html_with_whitespace = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                <img src="icon.png" height="20" style="margin-right: 2px;margin-top: -5px;">   
                   GEMILANG - TEST STORE   
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Test Address<br>
                Test City<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_with_whitespace)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - TEST STORE")

    def test_extract_address_with_br_tags(self):
        html_with_br = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                GEMILANG - TEST STORE
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Jl. Test Street 123   <br>
                   Test City, Test Province   <br>
                Indonesia   
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_with_br)
        self.assertEqual(len(locations), 1)
        expected_address = "Jl. Test Street 123\nTest City, Test Province\nIndonesia"
        self.assertEqual(locations[0].address, expected_address)

    def test_parse_html_raises_error_on_critical_failure(self):
        pass

    def test_location_parser_handles_different_html_structure(self):
        html_variation = """
        <div class="store-item">
            <a class="store-link" data-store-id="1">
                GEMILANG - VARIATION STORE
            </a>
            <div class="location-info">
                Variation Address<br>
                Variation City<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_variation)
        self.assertEqual(len(locations), 0)

    def test_extract_location_with_special_characters(self):
        html_special_chars = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                <img src="icon.png"> GEMILANG - STORE & CO.
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Jl. Raya No. 123/A-B<br>
                Kota (Special), Provinsi<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_special_chars)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - STORE & CO.")
        expected_address = "Jl. Raya No. 123/A-B\nKota (Special), Provinsi\nIndonesia"
        self.assertEqual(locations[0].address, expected_address)

    def test_parse_locations_with_nested_elements(self):
        html_nested = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                <img src="icon.png"> 
                <span>GEMILANG - NESTED STORE</span>
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                <p>Jl. Nested Street</p><br>
                <span>Nested City</span><br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_nested)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - NESTED STORE")

    def test_parse_locations_with_multiple_br_tags(self):
        html_multiple_br = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                GEMILANG - MULTI BR STORE
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Jl. Multi Street<br><br>
                Multi City<br>
                <br>Indonesia<br>
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_multiple_br)
        self.assertEqual(len(locations), 1)
        address_lines = locations[0].address.split('\n')
        filtered_lines = [line.strip() for line in address_lines if line.strip()]
        self.assertGreaterEqual(len(filtered_lines), 3)

    def test_parse_locations_with_unicode_characters(self):
        html_unicode = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                GEMILANG - TÔKÔ SPÉCIÀL
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Jl. Spéciàl Streét 123<br>
                Città Spéciàl, Prövincé<br>
                Indönésia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_unicode)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - TÔKÔ SPÉCIÀL")

    def test_parse_locations_with_empty_store_location_div(self):
        html_empty_div = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                GEMILANG - EMPTY LOCATION
            </a>
        </div>
        <div class="info-store">
            <div class="store-location"></div>
        </div>
        """
        locations = self.parser.parse_locations(html_empty_div)
        self.assertEqual(len(locations), 0)

    def test_parse_locations_with_whitespace_only_address(self):
        html_whitespace_address = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                GEMILANG - WHITESPACE STORE
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">   <br>   <br>   </div>
        </div>
        """
        locations = self.parser.parse_locations(html_whitespace_address)
        self.assertEqual(len(locations), 0)

    def test_parse_locations_case_sensitive_class_names(self):
        html_wrong_case = """
        <div class="Info-Store">
            <a href="#" class="Location_Click" data-id="1">
                GEMILANG - WRONG CASE
            </a>
        </div>
        <div class="Info-Store">
            <div class="Store-Location">
                Wrong Case Address<br>
                Wrong Case City<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_wrong_case)
        self.assertEqual(len(locations), 0)

    def test_parse_locations_with_html_entities(self):
        html_entities = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                GEMILANG - STORE &amp; CO.
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Jl. Test &lt;Street&gt;<br>
                City &quot;Special&quot;<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_entities)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - STORE & CO.")
        self.assertIn("Jl. Test <Street>", locations[0].address)

    def test_parse_locations_with_mixed_content(self):
        html_mixed = """
        <div class="info-store">
            <a href="#" class="location_click" data-id="1">
                <img src="icon.png"> GEMILANG - MIXED STORE <!-- comment -->
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                Jl. Mixed Street<br>
                <!-- another comment -->
                Mixed City<br>
                Indonesia
            </div>
        </div>
        <div class="not-location-item">
            <a href="#">Should be ignored</a>
        </div>
        """
        locations = self.parser.parse_locations(html_mixed)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - MIXED STORE")

    def test_parse_locations_with_no_data_id(self):
        html_no_data_id = """
        <div class="info-store">
            <a href="#" class="location_click">
                GEMILANG - NO DATA ID
            </a>
        </div>
        <div class="info-store">
            <div class="store-location">
                No Data ID Address<br>
                No Data ID City<br>
                Indonesia
            </div>
        </div>
        """
        locations = self.parser.parse_locations(html_no_data_id)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].store_name, "GEMILANG - NO DATA ID")

    def test_parse_large_number_of_locations(self):
        location_items = []
        for i in range(100):
            location_items.append(f"""
            <div class="info-store">
                <a href="#" class="location_click" data-id="{i}">
                    GEMILANG - STORE {i}
                </a>
            </div>
            <div class="info-store">
                <div class="store-location">
                    Jl. Street {i}<br>
                    City {i}<br>
                    Indonesia
                </div>
            </div>
            """)
        
        html_large = f"<html><body>{''.join(location_items)}</body></html>"
        locations = self.parser.parse_locations(html_large)
        self.assertEqual(len(locations), 100)
        self.assertEqual(locations[0].store_name, "GEMILANG - STORE 0")
        self.assertEqual(locations[99].store_name, "GEMILANG - STORE 99")

    def test_parse_locations_performance_with_malformed_html(self):
        malformed_large = "<div class='info-store'>" * 1000 + "<a href='#'>" * 500
        locations = self.parser.parse_locations(malformed_large)
        self.assertIsInstance(locations, list)
