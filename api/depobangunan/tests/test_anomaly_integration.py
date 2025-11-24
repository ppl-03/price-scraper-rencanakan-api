# api/depobangunan/tests/test_anomaly_integration.py
"""
Integration tests for DepoBangunan price anomaly detection and notification
"""

from django.test import TestCase
from db_pricing.models import PriceAnomaly, DepoBangunanProduct
from api.depobangunan.database_service import DepoBangunanDatabaseService


class TestDepoBangunanAnomalyIntegration(TestCase):
    """Test DepoBangunan anomaly detection and notification integration"""
    
    def setUp(self):
        """Set up test data"""
        PriceAnomaly.objects.all().delete()
        DepoBangunanProduct.objects.all().delete()
        self.service = DepoBangunanDatabaseService()
