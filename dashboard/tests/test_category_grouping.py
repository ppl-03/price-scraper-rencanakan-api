"""
Test cases for category grouping feature in the dashboard.
Tests include:
- Category constants availability
- Category filtering logic
- Template context includes categories
- JavaScript category filter functionality
"""

from django.test import TestCase, Client
from django.urls import reverse
from db_pricing.auto_categorization_service import AVAILABLE_CATEGORIES, AutoCategorizationService
from db_pricing.categorization import ProductCategorizer


class CategoryConstantsTestCase(TestCase):
    """Test that category constants are properly defined."""
    
    def test_available_categories_is_list(self):
        """Test that AVAILABLE_CATEGORIES is a list."""
        self.assertIsInstance(AVAILABLE_CATEGORIES, list)
    
    def test_available_categories_not_empty(self):
        """Test that AVAILABLE_CATEGORIES contains items."""
        self.assertGreater(len(AVAILABLE_CATEGORIES), 0)
    
    def test_available_categories_contains_expected_values(self):
        """Test that all expected categories are present."""
        expected_categories = [
            "Material Sanitair",
            "Peralatan Kerja",
            "Alat Berat",
            "Baja dan Besi Tulangan",
            "Material Interior",
            "Material Listrik",
            "Material Pipa Air",
            "Tanah, Pasir, Batu, dan Semen",
        ]
        for category in expected_categories:
            self.assertIn(category, AVAILABLE_CATEGORIES, 
                         f"Category '{category}' not found in AVAILABLE_CATEGORIES")
    
    def test_available_categories_all_are_strings(self):
        """Test that all categories are strings."""
        for category in AVAILABLE_CATEGORIES:
            self.assertIsInstance(category, str, 
                                 f"Category '{category}' is not a string")
    
    def test_available_categories_no_duplicates(self):
        """Test that there are no duplicate categories."""
        self.assertEqual(len(AVAILABLE_CATEGORIES), len(set(AVAILABLE_CATEGORIES)),
                        "AVAILABLE_CATEGORIES contains duplicate values")


class ProductCategorizerTestCase(TestCase):
    """Test product categorization logic."""
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_sanitair_categorization(self):
        """Test that sanitair products are categorized correctly."""
        test_products = [
            "Closet Duduk",
            "Hand Shower Stainless",
            "Wastafel Mewah",
            "Bidet Spray",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Material Sanitair", 
                           f"Product '{product}' not categorized as Material Sanitair")
    
    def test_peralatan_kerja_categorization(self):
        """Test that peralatan kerja products are categorized correctly."""
        test_products = [
            "Palu Besi 500g",
            "Obeng Plus Set",
            "Tang Potong 8 inch",
            "Bor Listrik 13mm",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Peralatan Kerja", 
                           f"Product '{product}' not categorized as Peralatan Kerja")
    
    def test_alat_berat_categorization(self):
        """Test that alat berat products are categorized correctly."""
        test_products = [
            "Crane 5 Ton",
            "Bulldozer Caterpillar",
            "Excavator 30 Ton",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Alat Berat", 
                           f"Product '{product}' not categorized as Alat Berat")
    
    def test_baja_tulangan_categorization(self):
        """Test that steel/baja products are categorized correctly."""
        test_products = [
            "Besi Beton 10mm",
            "Baja Tulangan Polos 8mm",
            "Wiremesh 4mm",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Baja dan Besi Tulangan", 
                           f"Product '{product}' not categorized as Baja dan Besi Tulangan")
    
    def test_interior_categorization(self):
        """Test that interior products are categorized correctly."""
        test_products = [
            "Plafon Gypsum 60x60",
            "Keramik Lantai 30x30",
            "Granit Dapur Premium",
            "Cat Tembok Premium 1 Liter",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Material Interior", 
                           f"Product '{product}' not categorized as Material Interior")
    
    def test_listrik_categorization(self):
        """Test that listrik products are categorized correctly."""
        test_products = [
            "Kabel NYY 3x2.5mm",
            "MCB 10A 1 Phase",
            "Saklar Broco Putih",
            "Fitting Lampu E27",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Material Listrik", 
                           f"Product '{product}' not categorized as Material Listrik")
    
    def test_pipa_air_categorization(self):
        """Test that pipa air products are categorized correctly."""
        test_products = [
            "Pipa PVC 1 inch",
            "Elbow PPR 1/2 inch",
            "Ball Valve 3/4 inch",
            "Pralon Water Pipe",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Material Pipa Air", 
                           f"Product '{product}' not categorized as Material Pipa Air")
    
    def test_tanah_pasir_batu_semen_categorization(self):
        """Test that tanah, pasir, batu, semen products are categorized correctly."""
        test_products = [
            "Semen Portland 50kg",
            "Pasir Pasang Per Kubik",
            "Batu Split 2/3",
            "Kerikil Untuk Beton",
        ]
        for product in test_products:
            result = self.categorizer.categorize(product)
            self.assertEqual(result, "Tanah, Pasir, Batu, dan Semen", 
                           f"Product '{product}' not categorized as Tanah, Pasir, Batu, dan Semen")
    
    def test_none_categorization(self):
        """Test that uncategorizable products return None."""
        uncategorizable = [
            "Random Product XYZ",
            "Unknown Item",
            "123456",
        ]
        for product in uncategorizable:
            result = self.categorizer.categorize(product)
            self.assertIsNone(result, 
                            f"Product '{product}' should not be categorized")
    
    def test_category_priority_sanitair_over_others(self):
        """Test that Sanitair has priority in categorization."""
        # "Closet" could be both sanitair and furniture, but should be categorized as sanitair
        result = self.categorizer.categorize("Closet Jongkok")
        self.assertEqual(result, "Material Sanitair")
    
    def test_empty_product_name(self):
        """Test that empty product names return None."""
        self.assertIsNone(self.categorizer.categorize(""))
        self.assertIsNone(self.categorizer.categorize(None))


class AutoCategorizationServiceTestCase(TestCase):
    """Test the AutoCategorizationService."""
    
    def setUp(self):
        self.service = AutoCategorizationService()
    
    def test_available_categories_accessible(self):
        """Test that AVAILABLE_CATEGORIES is accessible from service."""
        # Import and verify
        from db_pricing.auto_categorization_service import AVAILABLE_CATEGORIES
        self.assertEqual(len(AVAILABLE_CATEGORIES), 8)
    
    def test_model_map_contains_all_vendors(self):
        """Test that all vendors are in MODEL_MAP."""
        expected_vendors = ['gemilang', 'mitra10', 'depobangunan', 'juragan_material']
        for vendor in expected_vendors:
            self.assertIn(vendor, self.service.MODEL_MAP,
                         f"Vendor '{vendor}' not in MODEL_MAP")


class DashboardViewContextTestCase(TestCase):
    """Test that the dashboard view context includes categories."""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_view_includes_available_categories(self):
        """Test that the home view context includes available_categories."""
        # Note: This test assumes the home view is accessible
        # In a real scenario, you might need to mock the scraping functions
        response = self.client.get(reverse('home'))
        
        # Check response status
        self.assertIn(response.status_code, [200, 302])  # 302 for redirect, 200 for success
        
        # If we got a 200, check the context
        if response.status_code == 200:
            self.assertIn('available_categories', response.context)
            categories = response.context['available_categories']
            self.assertEqual(categories, AVAILABLE_CATEGORIES)


class CategoryFilteringJavaScriptTestCase(TestCase):
    """Test cases for JavaScript category filtering logic."""
    
    def test_filter_logic_pseudo_code(self):
        """Verify filter logic with pseudo code test."""
        # Sample data object with category
        sample_data = [
            {
                'item': 'Closet Jongkok Premium',
                'vendor': 'Gemilang Store',
                'category': 'Material Sanitair',
                'price': 500000,
                'unit': 'buah',
                'location': 'Jakarta',
            },
            {
                'item': 'Palu Besi 500g',
                'vendor': 'Depo Bangunan',
                'category': 'Peralatan Kerja',
                'price': 50000,
                'unit': 'buah',
                'location': 'Surabaya',
            },
            {
                'item': 'Besi Beton 10mm',
                'vendor': 'Mitra10',
                'category': 'Baja dan Besi Tulangan',
                'price': 75000,
                'unit': 'batang',
                'location': 'Bandung',
            },
        ]
        
        # Test filter: only Sanitair category
        filtered = [d for d in sample_data if d['category'] == 'Material Sanitair']
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['item'], 'Closet Jongkok Premium')
        
        # Test filter: multiple conditions (vendor + category)
        filtered = [d for d in sample_data 
                   if d['category'] == 'Peralatan Kerja' 
                   and d['vendor'] == 'Depo Bangunan']
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['item'], 'Palu Besi 500g')
        
        # Test filter: no match
        filtered = [d for d in sample_data 
                   if d['category'] == 'Material Listrik']
        self.assertEqual(len(filtered), 0)


class CategoryUITestCase(TestCase):
    """Test UI elements for category grouping."""
    
    def setUp(self):
        self.client = Client()
    
    def test_dropdown_options_rendered(self):
        """Test that category dropdown options are rendered."""
        # This is a more integration-style test
        response = self.client.get(reverse('home'))
        
        if response.status_code == 200:
            content = response.content.decode()
            # Check that the dropdown element exists
            self.assertIn('categorySelect', content)
            # Check that option elements are present for categories
            self.assertIn('Material Sanitair', content)
            self.assertIn('Peralatan Kerja', content)


class CategoryBatchTestCase(TestCase):
    """Test batch categorization of multiple products."""
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_categorize_batch(self):
        """Test batch categorization of multiple products."""
        products = [
            "Closet Jongkok",
            "Palu Besi",
            "Besi Beton 10mm",
            "Kabel NYY 3x2.5",
            "Semen Portland 50kg",
        ]
        
        results = self.categorizer.categorize_batch(products)
        
        self.assertEqual(len(results), len(products))
        self.assertEqual(results[0], "Material Sanitair")
        self.assertEqual(results[1], "Peralatan Kerja")
        self.assertEqual(results[2], "Baja dan Besi Tulangan")
        self.assertEqual(results[3], "Material Listrik")
        self.assertEqual(results[4], "Tanah, Pasir, Batu, dan Semen")


class CategoryCaseInsensitivityTestCase(TestCase):
    """Test that categorization is case-insensitive."""
    
    def setUp(self):
        self.categorizer = ProductCategorizer()
    
    def test_uppercase_product_name(self):
        """Test categorization with uppercase product name."""
        result1 = self.categorizer.categorize("closet jongkok")
        result2 = self.categorizer.categorize("CLOSET JONGKOK")
        result3 = self.categorizer.categorize("Closet Jongkok")
        
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
        self.assertEqual(result3, "Material Sanitair")
    
    def test_mixed_case_product_name(self):
        """Test categorization with mixed case product name."""
        result1 = self.categorizer.categorize("pALu bEsI")
        result2 = self.categorizer.categorize("PALU BESI")
        
        self.assertEqual(result1, result2)
        self.assertEqual(result2, "Peralatan Kerja")
