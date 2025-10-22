from db_pricing.models import Mitra10Product
from api.mitra10.database_service import Mitra10DatabaseService
from .test_base import MySQLTestCase


class TestSaveWithPriceUpdate(MySQLTestCase):
    
    def test_insert_new_product(self):
        service = Mitra10DatabaseService()
        data = [{"name": "New Product", "price": 10000, "url": "https://test.com/new", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
        self.assertEqual(Mitra10Product.objects.count(), 1)
    
    def test_update_existing_product_price_changed(self):
        Mitra10Product.objects.create(name="Product A", price=10000, url="https://test.com/a", unit="KG")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product A", "price": 12000, "url": "https://test.com/a", "unit": "KG"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(Mitra10Product.objects.count(), 1)
        
        updated_product = Mitra10Product.objects.get(name="Product A")
        self.assertEqual(updated_product.price, 12000)
    
    def test_no_update_when_price_same(self):
        Mitra10Product.objects.create(name="Product B", price=10000, url="https://test.com/b", unit="M")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product B", "price": 10000, "url": "https://test.com/b", "unit": "M"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(Mitra10Product.objects.count(), 1)
    
    def test_anomaly_detection_price_increase_15_percent(self):
        Mitra10Product.objects.create(name="Product C", price=10000, url="https://test.com/c", unit="PCS")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product C", "price": 11500, "url": "https://test.com/c", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["name"], "Product C")
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 11500)
        self.assertEqual(anomaly["change_percent"], 15.0)
    
    def test_anomaly_detection_price_decrease_15_percent(self):
        Mitra10Product.objects.create(name="Product D", price=10000, url="https://test.com/d", unit="KG")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product D", "price": 8500, "url": "https://test.com/d", "unit": "KG"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 1)
        
        anomaly = result["anomalies"][0]
        self.assertEqual(anomaly["old_price"], 10000)
        self.assertEqual(anomaly["new_price"], 8500)
        self.assertEqual(anomaly["change_percent"], -15.0)
    
    def test_no_anomaly_price_increase_14_percent(self):
        Mitra10Product.objects.create(name="Product E", price=10000, url="https://test.com/e", unit="M")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product E", "price": 11400, "url": "https://test.com/e", "unit": "M"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_no_anomaly_price_decrease_14_percent(self):
        Mitra10Product.objects.create(name="Product F", price=10000, url="https://test.com/f", unit="PCS")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product F", "price": 8600, "url": "https://test.com/f", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_anomaly_detection_price_increase_20_percent(self):
        Mitra10Product.objects.create(name="Product G", price=10000, url="https://test.com/g", unit="BOX")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product G", "price": 12000, "url": "https://test.com/g", "unit": "BOX"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 1)
        self.assertEqual(result["anomalies"][0]["change_percent"], 20.0)
    
    def test_anomaly_detection_price_decrease_30_percent(self):
        Mitra10Product.objects.create(name="Product H", price=10000, url="https://test.com/h", unit="KG")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product H", "price": 7000, "url": "https://test.com/h", "unit": "KG"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["anomalies"]), 1)
        self.assertEqual(result["anomalies"][0]["change_percent"], -30.0)
    
    def test_multiple_products_mixed_operations(self):
        Mitra10Product.objects.create(name="Existing 1", price=10000, url="https://test.com/ex1", unit="PCS")
        Mitra10Product.objects.create(name="Existing 2", price=20000, url="https://test.com/ex2", unit="KG")
        
        service = Mitra10DatabaseService()
        data = [
            {"name": "Existing 1", "price": 11000, "url": "https://test.com/ex1", "unit": "PCS"},
            {"name": "Existing 2", "price": 20000, "url": "https://test.com/ex2", "unit": "KG"},
            {"name": "New Product", "price": 15000, "url": "https://test.com/new", "unit": "M"}
        ]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(Mitra10Product.objects.count(), 3)
    
    def test_multiple_anomalies_detected(self):
        Mitra10Product.objects.create(name="Product I", price=10000, url="https://test.com/i", unit="PCS")
        Mitra10Product.objects.create(name="Product J", price=20000, url="https://test.com/j", unit="KG")
        
        service = Mitra10DatabaseService()
        data = [
            {"name": "Product I", "price": 11500, "url": "https://test.com/i", "unit": "PCS"},
            {"name": "Product J", "price": 17000, "url": "https://test.com/j", "unit": "KG"}
        ]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 2)
        self.assertEqual(len(result["anomalies"]), 2)
    
    def test_empty_data_returns_false(self):
        service = Mitra10DatabaseService()
        data = []
        
        result = service.save_with_price_update(data)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_invalid_data_returns_false(self):
        service = Mitra10DatabaseService()
        data = [{"name": "Invalid", "price": -100, "url": "https://test.com", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertFalse(result["success"])
    
    def test_same_name_different_url_creates_new(self):
        Mitra10Product.objects.create(name="Product K", price=10000, url="https://test.com/k1", unit="PCS")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product K", "price": 10000, "url": "https://test.com/k2", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(Mitra10Product.objects.count(), 2)
    
    def test_same_name_different_unit_creates_new(self):
        Mitra10Product.objects.create(name="Product L", price=10000, url="https://test.com/l", unit="PCS")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product L", "price": 10000, "url": "https://test.com/l", "unit": "KG"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(Mitra10Product.objects.count(), 2)
    
    def test_zero_old_price_no_division_error(self):
        Mitra10Product.objects.create(name="Product M", price=0, url="https://test.com/m", unit="PCS")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product M", "price": 1000, "url": "https://test.com/m", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["anomalies"]), 0)
    
    def test_price_update_changes_updated_at(self):
        product = Mitra10Product.objects.create(name="Product N", price=10000, url="https://test.com/n", unit="PCS")
        original_updated_at = product.updated_at
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product N", "price": 12000, "url": "https://test.com/n", "unit": "PCS"}]
        
        result = service.save_with_price_update(data)
        
        self.assertTrue(result["success"])
        updated_product = Mitra10Product.objects.get(id=product.id)
        self.assertGreater(updated_product.updated_at, original_updated_at)
    
    def test_anomaly_fields_completeness(self):
        Mitra10Product.objects.create(name="Product O", price=10000, url="https://test.com/o", unit="M")
        
        service = Mitra10DatabaseService()
        data = [{"name": "Product O", "price": 11600, "url": "https://test.com/o", "unit": "M"}]
        
        result = service.save_with_price_update(data)
        
        self.assertEqual(len(result["anomalies"]), 1)
        anomaly = result["anomalies"][0]
        self.assertIn("name", anomaly)
        self.assertIn("url", anomaly)
        self.assertIn("unit", anomaly)
        self.assertIn("old_price", anomaly)
        self.assertIn("new_price", anomaly)
        self.assertIn("change_percent", anomaly)
