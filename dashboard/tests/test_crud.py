from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from dashboard import models 

class CrudCuratedPriceTests(TestCase):
    def setUp(self):
        self.unit = models.Unit.objects.create(name="sak")
        self.prov = models.Province.objects.create(name="DKI Jakarta")
        self.grp  = models.ItemPriceGroup.objects.create(name="Material")
        self.item = models.ItemPrice.objects.create(
            id="CEM001", item_price_group=self.grp, unit=self.unit, name="Semen Portland"
        )

    def test_list_page_renders(self):
        r = self.client.get(reverse("curated_price_list"))
        self.assertEqual(r.status_code, 200)

    def test_create_curated_price(self):
        r = self.client.post(reverse("curated_price_create"), {
            "item_price": self.item.pk,
            "province": self.prov.pk,
            "price": "35000.00",
        })
        self.assertEqual(r.status_code, 302)
        row = models.ItemPriceProvince.objects.get(item_price=self.item, province=self.prov)
        self.assertEqual(row.price, Decimal("35000.00"))

    def test_update_curated_price(self):
        row = models.ItemPriceProvince.objects.create(item_price=self.item, province=self.prov, price="35000.00")
        r = self.client.post(reverse("curated_price_update", args=[row.pk]), {
            "item_price": self.item.pk,
            "province": self.prov.pk,
            "price": "36000.00",
        })
        self.assertEqual(r.status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.price, Decimal("36000.00"))

    def test_delete_curated_price(self):
        row = models.ItemPriceProvince.objects.create(item_price=self.item, province=self.prov, price="35000.00")
        r = self.client.post(reverse("curated_price_delete", args=[row.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(models.ItemPriceProvince.objects.filter(pk=row.pk).exists())

    def test_prefill_from_scrape_renders_form(self):
        r = self.client.post(reverse("curated_price_from_scrape"), {
            "name": "Semen A",
            "value": "30000",
            "source": "Mitra10",
            "url": "https://example.com/p"
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Save Price from Scrape")

    def test_validation_price_must_be_positive(self):
        r = self.client.post(reverse("curated_price_create"), {
            "item_price": self.item.pk,
            "province": self.prov.pk,
            "price": "0",
        })
        self.assertEqual(r.status_code, 200)  # stays on form
        self.assertContains(r, "Price must be greater than 0.")