from django.test import TestCase
from django.db.models import ProtectedError
from db_pricing.models import Item, Unit, ItemPrice, Province

class PriceRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.item = Item.objects.create(code="CEM001", name="Cement")
        cls.unit = Unit.objects.create(code="kg", name="Kilogram")
        cls.prov = Province.objects.create(code="JKT", name="Jakarta")

    def test_price_cannot_be_negative(self):
        with self.assertRaises(Exception):
            ItemPrice.objects.create(
                item=self.item,
                unit=self.unit,
                province=self.prov,
                value=-1,
                is_latest=True
            )

    def test_item_code_must_be_unique(self):
        with self.assertRaises(Exception):
            Item.objects.create(code="CEM001", name="Duplicate Cement")

    def test_only_one_latest_per_item_province(self):
        ItemPrice.objects.create(
            item=self.item,
            unit=self.unit,
            province=self.prov,
            value=10000,
            is_latest=True
        )
        with self.assertRaises(Exception):
            ItemPrice.objects.create(
                item=self.item,
                unit=self.unit,
                province=self.prov,
                value=12000,
                is_latest=True
            )

    def test_cannot_delete_item_if_priced(self):
        ItemPrice.objects.create(
            item=self.item,
            unit=self.unit,
            province=self.prov,
            value=12000,
            is_latest=True
        )
        with self.assertRaises(ProtectedError):
            self.item.delete()