from decimal import Decimal
from django.test import TestCase
from django.db.models import ProtectedError
from django.core.exceptions import ValidationError

from db_pricing.models import Item, Unit, ItemPrice, Province
from db_pricing.services import default_price_creation_service

class PriceRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.item = Item.objects.create(code="CEM001", name="Cement")
        cls.unit = Unit.objects.create(code="kg", name="Kilogram")
        cls.prov = Province.objects.create(code="JKT", name="Jakarta")

    def test_price_cannot_be_negative(self):
        service = default_price_creation_service()
        with self.assertRaises(ValidationError):
            service.create_price(
                item_id=self.item.id,
                unit_id=self.unit.id,
                province_id=self.prov.id,
                value=Decimal("-1"),
                is_latest=True,
            )

    def test_item_code_must_be_unique(self):
        with self.assertRaises(Exception):
            Item.objects.create(code="CEM001", name="Duplicate Cement")

    def test_only_one_latest_per_item_province(self):
        service = default_price_creation_service()
        service.create_price(
            item_id=self.item.id,
            unit_id=self.unit.id,
            province_id=self.prov.id,
            value=Decimal("10000"),
            is_latest=True,
        )
        with self.assertRaises(ValidationError):
            service.create_price(
                item_id=self.item.id,
                unit_id=self.unit.id,
                province_id=self.prov.id,
                value=Decimal("12000"),
                is_latest=True,
            )

    def test_cannot_delete_item_if_priced(self):
        service = default_price_creation_service()
        service.create_price(
            item_id=self.item.id,
            unit_id=self.unit.id,
            province_id=self.prov.id,
            value=Decimal("12000"),
            is_latest=True,
        )
        with self.assertRaises(ProtectedError):
            self.item.delete()