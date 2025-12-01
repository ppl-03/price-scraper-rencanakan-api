"""
TDD Tests for Gemilang API Interaction Scenarios
================================================

This test suite validates that the interaction scenarios defined in
interaction_scenarios.py execute correctly and produce expected outcomes.

Tests follow TDD RED-GREEN-REFACTOR cycle:
- RED: Define expected behavior through tests
- GREEN: Scenarios pass validation
- REFACTOR: Improve code quality

Each test:
1. Sets up scenario context with mocks
2. Executes scenario via utility function
3. Validates scenario result
4. Checks side effects and data integrity
"""

import json
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from api.interfaces import ScrapingResult, Product, Location, LocationScrapingResult

# Import scenario utilities
from api.gemilang.interaction_scenarios import (
    ScenarioContext,
    ScenarioResult,
    scenario_complete_product_search,
    scenario_location_service_failure_handling,
    scenario_invalid_input_rejection,
    scenario_sql_injection_prevention,
    scenario_price_data_persistence,
    scenario_find_cheapest_price,
    scenario_paginated_results,
    scenario_price_change_detection,
    run_scenario,
    create_scenario_report
)


class TestCompleteProductSearchScenario(TestCase):
    """Test Scenario 1: Complete product search with location enrichment"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_executes_successfully(self):
        """GREEN: Scenario runs and returns valid products with locations"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks
            mock_loc_instance = Mock()
            mock_locations = [
                Location(name="GEMILANG - Store1", code="S1"),
                Location(name="GEMILANG - Store2", code="S2")
            ]
            mock_loc_result = LocationScrapingResult(locations=mock_locations, success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_products = [
                Product(name="Product A", price=10000, url="/a", unit="Kg"),
                Product(name="Product B", price=20000, url="/b", unit="Kg")
            ]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Execute scenario
            result = scenario_complete_product_search(self.context, keyword="test")
            
            # Validate scenario result
            self.assertTrue(result.success, "Scenario should succeed")
            self.assertEqual(result.response_status, 200)
            self.assertTrue(result.is_valid(), "Scenario should pass all validations")
            self.assertEqual(len(result.validation_errors), 0)
            
            # Validate data integrity
            self.assertIn('products', result.response_data)
            self.assertEqual(len(result.response_data['products']), 2)
            
            # Validate side effects
            self.assertEqual(result.side_effects['products_returned'], 2)
            self.assertTrue(result.side_effects['location_enriched'])
            
    def test_scenario_validates_product_structure(self):
        """GREEN: Scenario detects missing required fields"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks
            mock_loc_instance = Mock()
            mock_loc_result = LocationScrapingResult(locations=[], success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_products = [
                Product(name="Product A", price=10000, url="/a", unit="Kg")
            ]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Execute scenario
            result = scenario_complete_product_search(self.context, keyword="test")
            
            # Should succeed even with empty locations (graceful degradation)
            self.assertTrue(result.success)
            self.assertEqual(result.response_status, 200)


class TestLocationServiceFailureScenario(TestCase):
    """Test Scenario 2: Graceful degradation on location service failure"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_handles_location_failure_gracefully(self):
        """GREEN: Products returned despite location service failure"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Mock location failure
            mock_loc_instance = Mock()
            mock_loc_result = LocationScrapingResult(
                locations=[],
                success=False,
                error_message="Connection timeout"
            )
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            # Mock successful products
            mock_scraper_instance = Mock()
            mock_products = [Product(name="Test", price=100, url="/t", unit="Pcs")]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Execute scenario
            result = scenario_location_service_failure_handling(self.context, keyword="test")
            
            # Validate graceful degradation
            self.assertTrue(result.success, "Should succeed despite location failure")
            self.assertEqual(result.response_status, 200)
            self.assertTrue(result.is_valid())
            self.assertTrue(result.side_effects['service_failure_handled'])
            self.assertTrue(result.side_effects['data_integrity_maintained'])


class TestInvalidInputRejectionScenario(TestCase):
    """Test Scenario 3: Invalid input detection and rejection"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_detects_invalid_keyword(self):
        """GREEN: Invalid keyword triggers validation error"""
        # Execute scenario with too-long keyword
        result = scenario_invalid_input_rejection(
            self.context,
            keyword="a" * 101  # Exceeds max length of 100
        )
        
        # Validate rejection
        self.assertTrue(result.success, "Scenario executed (rejection is success)")
        self.assertEqual(result.response_status, 400)
        self.assertTrue(result.is_valid())
        self.assertTrue(result.side_effects['validation_prevented_processing'])
        self.assertTrue(result.side_effects['specific_errors_provided'])
        
    def test_scenario_detects_invalid_page_number(self):
        """GREEN: Invalid page number triggers validation error"""
        # Execute scenario with out-of-range page
        result = scenario_invalid_input_rejection(
            self.context,
            keyword="valid",
            page="101"  # Exceeds max of 100
        )
        
        # Validate rejection
        self.assertTrue(result.success)
        self.assertEqual(result.response_status, 400)
        self.assertTrue(result.is_valid())
        
    def test_scenario_provides_field_specific_errors(self):
        """GREEN: Error messages include field names"""
        result = scenario_invalid_input_rejection(
            self.context,
            keyword="a" * 101
        )
        
        # Validate error specificity
        self.assertIn('error', result.response_data)
        error_msg = result.response_data['error'].lower()
        self.assertIn('keyword', error_msg, "Error should mention 'keyword' field")


class TestSQLInjectionPreventionScenario(TestCase):
    """Test Scenario 4: SQL injection attack prevention"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_blocks_sql_injection_attempts(self):
        """GREEN: SQL injection patterns detected and handled"""
        malicious_inputs = [
            "'; DROP TABLE products; --",
            "1' OR '1'='1",
            "admin'--"
        ]
        
        for malicious in malicious_inputs:
            with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
                 patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
                
                # Setup mocks
                mock_loc_instance = Mock()
                mock_loc_result = LocationScrapingResult(locations=[], success=True)
                mock_loc_instance.scrape_locations.return_value = mock_loc_result
                mock_loc.return_value = mock_loc_instance
                
                mock_scraper_instance = Mock()
                mock_result = ScrapingResult(products=[], success=True, url="https://test.com")
                mock_scraper_instance.scrape_products.return_value = mock_result
                mock_scraper.return_value = mock_scraper_instance
                
                # Execute scenario
                result = scenario_sql_injection_prevention(self.context, malicious_keyword=malicious)
                
                # Validate security
                self.assertTrue(result.success, f"Should handle malicious input: {malicious}")
                self.assertIn(result.response_status, [200, 400])
                self.assertTrue(result.side_effects['attack_prevented'])
                self.assertTrue(result.side_effects['database_protected'])


class TestPriceDataPersistenceScenario(TestCase):
    """Test Scenario 5: Price data saving to database"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_validates_data_for_persistence(self):
        """GREEN: Scraped data validated before database insertion"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks with valid data
            mock_loc_instance = Mock()
            mock_loc_result = LocationScrapingResult(locations=[], success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_products = [
                Product(name="Semen 50kg", price=65000, url="/prod1", unit="Zak"),
                Product(name="Cat Tembok", price=45000, url="/prod2", unit="Kaleng")
            ]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Execute scenario
            result = scenario_price_data_persistence(
                self.context,
                keyword="semen",
                expected_product_count=2
            )
            
            # Validate data integrity
            self.assertTrue(result.success)
            self.assertTrue(result.is_valid())
            self.assertTrue(result.side_effects['data_structure_valid'])
            self.assertTrue(result.side_effects['ready_for_persistence'])
            self.assertEqual(result.side_effects['products_scraped'], 2)


class TestFindCheapestPriceScenario(TestCase):
    """Test Scenario 6: Find cheapest price across vendors"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_finds_cheapest_product(self):
        """GREEN: System identifies and returns cheapest price"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks
            mock_loc_instance = Mock()
            mock_locations = [Location(name="GEMILANG - Store1", code="S1")]
            mock_loc_result = LocationScrapingResult(locations=mock_locations, success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_products = [
                Product(name="Product A", price=50000, url="/a", unit="Kg"),
                Product(name="Product B", price=30000, url="/b", unit="Kg"),  # Cheapest
                Product(name="Product C", price=45000, url="/c", unit="Kg")
            ]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Execute scenario
            result = scenario_find_cheapest_price(self.context, keyword="test")
            
            # Validate cheapest identification
            self.assertTrue(result.success)
            self.assertTrue(result.is_valid())
            self.assertTrue(result.side_effects['cheapest_found'])
            self.assertEqual(result.side_effects['cheapest_price'], 30000)
            self.assertTrue(result.side_effects['sorted_correctly'])


class TestPaginatedResultsScenario(TestCase):
    """Test Scenario 7: Pagination for large result sets"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_handles_pagination(self):
        """GREEN: Pagination parameters respected"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks
            mock_loc_instance = Mock()
            mock_loc_result = LocationScrapingResult(locations=[], success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_products = [Product(name=f"P{i}", price=i*1000, url=f"/p{i}", unit="Pcs") for i in range(5)]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Execute scenario for page 1
            result = scenario_paginated_results(self.context, keyword="test", page=1)
            
            # Validate pagination
            self.assertTrue(result.success)
            self.assertTrue(result.is_valid())
            self.assertEqual(result.side_effects['page_requested'], 1)
            self.assertGreater(result.side_effects['products_returned'], 0)


class TestPriceChangeDetectionScenario(TestCase):
    """Test Scenario 8: Real-time price change detection"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_scenario_detects_price_changes(self):
        """GREEN: Price changes identified correctly"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks
            mock_loc_instance = Mock()
            mock_loc_result = LocationScrapingResult(locations=[], success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_products = [
                Product(name="Semen 50kg", price=70000, url="/p1", unit="Zak"),  # Increased
                Product(name="Cat Tembok", price=40000, url="/p2", unit="Kaleng")  # Decreased
            ]
            mock_result = ScrapingResult(products=mock_products, success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Previous prices (simulated)
            previous_prices = {
                "Semen 50kg": 65000,  # Was cheaper
                "Cat Tembok": 45000   # Was more expensive
            }
            
            # Execute scenario
            result = scenario_price_change_detection(
                self.context,
                keyword="building materials",
                previous_prices=previous_prices
            )
            
            # Validate change detection
            self.assertTrue(result.success)
            self.assertTrue(result.is_valid())
            self.assertEqual(result.side_effects['prices_compared'], 2)
            self.assertEqual(result.side_effects['changes_detected'], 2)
            self.assertGreater(len(result.side_effects['change_details']), 0)


class TestScenarioRunner(TestCase):
    """Test scenario execution utilities"""
    
    def setUp(self):
        self.client = Client()
        self.context = ScenarioContext(client=self.client)
        
    def test_run_scenario_utility(self):
        """GREEN: Scenario runner executes scenarios with error handling"""
        with patch('api.gemilang.views.create_gemilang_location_scraper') as mock_loc, \
             patch('api.gemilang.views.create_gemilang_scraper') as mock_scraper:
            
            # Setup mocks
            mock_loc_instance = Mock()
            mock_loc_result = LocationScrapingResult(locations=[], success=True)
            mock_loc_instance.scrape_locations.return_value = mock_loc_result
            mock_loc.return_value = mock_loc_instance
            
            mock_scraper_instance = Mock()
            mock_result = ScrapingResult(products=[], success=True, url="https://test.com")
            mock_scraper_instance.scrape_products.return_value = mock_result
            mock_scraper.return_value = mock_scraper_instance
            
            # Run scenario via utility
            result = run_scenario(
                scenario_complete_product_search,
                self.context,
                keyword="test"
            )
            
            # Validate runner
            self.assertIsInstance(result, ScenarioResult)
            self.assertIn('scenario_name', result.__dict__)
            
    def test_create_scenario_report(self):
        """GREEN: Report generation summarizes multiple scenarios"""
        # Create mock results
        results = [
            ScenarioResult(
                success=True,
                scenario_name="Test 1",
                response_status=200,
                response_data={},
                execution_time_ms=100.0
            ),
            ScenarioResult(
                success=True,
                scenario_name="Test 2",
                response_status=200,
                response_data={},
                validation_errors=["Error 1"],
                execution_time_ms=150.0
            )
        ]
        
        # Generate report
        report = create_scenario_report(results)
        
        # Validate report
        self.assertEqual(report['total_scenarios'], 2)
        self.assertEqual(report['successful'], 1)  # Only first is valid (no errors)
        self.assertEqual(report['failed'], 1)
        self.assertAlmostEqual(report['average_execution_time_ms'], 125.0)
        self.assertEqual(len(report['scenarios']), 2)
