from django.test import TestCase
from dashboard import models

class ItemPriceModelTests(TestCase):
    def setUp(self):
        self.unit = models.Unit.objects.create(name='meter')
        self.province1 = models.Province.objects.create(name='Province A')
        self.province2 = models.Province.objects.create(name='Province B')
        self.group = models.ItemPriceGroup.objects.create(name='Concrete')

        self.item = models.ItemPrice.objects.create(id='item-1', item_price_group=self.group, unit=self.unit, name='Item 1')
        models.ItemPriceProvince.objects.create(item_price=self.item, province=self.province1, price='12.34')
        models.ItemPriceProvince.objects.create(item_price=self.item, province=self.province2, price='56.78')

    def test_price_relationship_returns_all_rows(self):
        prices = list(self.item.price())
        self.assertEqual(len(prices), 2)
        self.assertEqual(str(prices[0].price), '12.34')

    def test_with_price_by_province_prefetches_only_one(self):
        qs = models.ItemPrice.with_price_by_province(self.province1.id)
        item = qs.get(id='item-1')
        # with_price_by_province attaches results to 'price_filtered'
        self.assertTrue(hasattr(item, 'price_filtered'))
        self.assertEqual(len(item.price_filtered), 1)
        self.assertEqual(str(item.price_filtered[0].price), '12.34')

    def test_item_price_group_relationship(self):
        self.assertEqual(self.item.item_price_group, self.group)

    def test_unit_relationship_exists(self):
        # ensure select_related is possible; basic relation check
        self.assertEqual(self.item.unit, self.unit)
