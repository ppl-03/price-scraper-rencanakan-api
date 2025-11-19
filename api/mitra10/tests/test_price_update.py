from db_pricing.models import Mitra10Product
from api.mitra10.database_service import Mitra10DatabaseService
from .test_base import MySQLTestCase


class TestSaveWithPriceUpdate(MySQLTestCase):
    """Comprehensive tests for Mitra10 price update and anomaly detection."""

    def setUp(self):
        self.service = Mitra10DatabaseService()

    def _create_product(self, name, price=10000, url=None, unit="PCS"):
        """Helper to simplify repetitive product creation."""
        return Mitra10Product.objects.create(
            name=name, price=price, url=url or f"https://test.com/{name.lower()}", unit=unit
        )

    def _save_and_assert(self, data, success=True, inserted=0, updated=0, anomalies=0):
        """Helper to perform save and validate results."""
        result = self.service.save_with_price_update(data)
        assert result["success"] == success
        assert result["inserted"] == inserted
        assert result["updated"] == updated
        assert len(result["anomalies"]) == anomalies
        return result

    def test_insert_new_product(self):
        data = [{"name": "New Product", "price": 10000, "url": "https://test.com/new", "unit": "PCS"}]
        self._save_and_assert(data, inserted=1)
        assert Mitra10Product.objects.count() == 1

    def test_update_existing_product_price_changed(self):
        self._create_product("Product A", 10000, "https://test.com/a", "KG")
        data = [{"name": "Product A", "price": 12000, "url": "https://test.com/a", "unit": "KG"}]
        # 20% increase = anomaly detected, price should NOT update (updated=0)
        self._save_and_assert(data, updated=0, anomalies=1)
        # Price should remain old price because anomaly needs approval
        assert Mitra10Product.objects.get(name="Product A").price == 10000

    def test_no_update_when_price_same(self):
        self._create_product("Product B", 10000, "https://test.com/b", "M")
        data = [{"name": "Product B", "price": 10000, "url": "https://test.com/b", "unit": "M"}]
        self._save_and_assert(data)

    def test_anomaly_detection(self):
        """Tests multiple anomaly scenarios for ±15% threshold."""
        scenarios = [
            ("Product C", 10000, 11500, 15.0),
            ("Product D", 10000, 8500, -15.0),
            ("Product G", 10000, 12000, 20.0),
            ("Product H", 10000, 7000, -30.0),
        ]
        for name, old_price, new_price, change in scenarios:
            self._create_product(name, old_price, f"https://test.com/{name.lower()}", "PCS")
            data = [{"name": name, "price": new_price, "url": f"https://test.com/{name.lower()}", "unit": "PCS"}]
            # Anomalies detected (>=15% change), so updated=0 (price does NOT update)
            result = self._save_and_assert(data, updated=0, anomalies=1)
            assert result["anomalies"][0]["change_percent"] == change

    def test_no_anomaly_under_15_percent(self):
        self._create_product("Product E", 10000, "https://test.com/e", "M")
        self._create_product("Product F", 10000, "https://test.com/f", "PCS")

        cases = [
            [{"name": "Product E", "price": 11400, "url": "https://test.com/e", "unit": "M"}],
            [{"name": "Product F", "price": 8600, "url": "https://test.com/f", "unit": "PCS"}],
        ]
        for data in cases:
            self._save_and_assert(data, updated=1)

    def test_multiple_operations_and_anomalies(self):
        self._create_product("Existing 1", 10000, "https://test.com/ex1", "PCS")
        self._create_product("Existing 2", 20000, "https://test.com/ex2", "KG")

        mixed_data = [
            {"name": "Existing 1", "price": 11000, "url": "https://test.com/ex1", "unit": "PCS"},  # 10% increase, auto-updates
            {"name": "Existing 2", "price": 20000, "url": "https://test.com/ex2", "unit": "KG"},  # No change
            {"name": "New Product", "price": 15000, "url": "https://test.com/new", "unit": "M"},  # New insert
        ]
        self._save_and_assert(mixed_data, inserted=1, updated=1)
        assert Mitra10Product.objects.count() == 3

        # Both products have >=15% price changes, triggering anomalies
        anomalies_data = [
            {"name": "Product I", "price": 11500, "url": "https://test.com/i", "unit": "PCS"},
            {"name": "Product J", "price": 17000, "url": "https://test.com/j", "unit": "KG"},
        ]
        self._create_product("Product I", 10000, "https://test.com/i", "PCS")
        self._create_product("Product J", 20000, "https://test.com/j", "KG")
        # Both are anomalies (>=15% change), so updated=0 (neither price updates)
        self._save_and_assert(anomalies_data, updated=0, anomalies=2)

    def test_edge_cases(self):
        invalid_data = [{"name": "Invalid", "price": -100, "url": "https://test.com", "unit": "PCS"}]
        empty_data = []
        self._save_and_assert(empty_data, success=False)
        self._save_and_assert(invalid_data, success=False)

    def test_same_name_different_variants(self):
        """Tests that unique products by URL or unit are inserted separately."""
        self._create_product("Product K", 10000, "https://test.com/k1", "PCS")
        data_1 = [{"name": "Product K", "price": 10000, "url": "https://test.com/k2", "unit": "PCS"}]
        data_2 = [{"name": "Product L", "price": 10000, "url": "https://test.com/l", "unit": "KG"}]
        self._save_and_assert(data_1, inserted=1)
        self._save_and_assert(data_2, inserted=1)
        assert Mitra10Product.objects.count() == 3
