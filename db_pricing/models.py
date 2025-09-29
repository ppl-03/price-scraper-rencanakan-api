# db_pricing/models.py
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.deletion import PROTECT


class Item(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} — {self.name}"


class Unit(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} — {self.name}"


class Province(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} — {self.name}"


class ItemPrice(models.Model):
    item = models.ForeignKey(Item, on_delete=PROTECT, related_name="prices")
    unit = models.ForeignKey(Unit, on_delete=PROTECT, related_name="prices")
    province = models.ForeignKey(Province, on_delete=PROTECT, related_name="prices")
    value = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    is_latest = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "province"],
                condition=Q(is_latest=True),
                name="uq_latest_price_per_item_province",
            ),
        ]

    def __str__(self):  # Keep representation, heavy validation handled by service layer
        return f"{self.item.code} @ {self.province.code} ({self.unit.code}) — {self.value}"