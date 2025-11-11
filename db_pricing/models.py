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

    def __str__(self):
        return f"{self.item.code} @ {self.province.code} ({self.unit.code}) — {self.value}"


class GemilangProduct(models.Model):
    name = models.CharField(max_length=500)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    url = models.URLField(max_length=1000)
    unit = models.CharField(max_length=50, blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='', db_default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gemilang_products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} - Rp{self.price}"


class Mitra10Product(models.Model):
    name = models.CharField(max_length=500)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    url = models.URLField(max_length=1000)
    unit = models.CharField(max_length=50, blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='', db_default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mitra10_products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} - Rp{self.price}"
      
      
class DepoBangunanProduct(models.Model):
    name = models.CharField(max_length=500)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    url = models.URLField(max_length=1000)
    unit = models.CharField(max_length=50, blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='', db_default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'depobangunan_products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} - Rp{self.price}"


class JuraganMaterialProduct(models.Model):
    name = models.CharField(max_length=500)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    url = models.URLField(max_length=1000)
    unit = models.CharField(max_length=50, blank=True, default='')
    location = models.CharField(max_length=200, default='')
    category = models.CharField(max_length=100, blank=True, default='', db_default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'juragan_material_products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} - Rp{self.price}"


class TokopediaProduct(models.Model):
    name = models.CharField(max_length=500)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    url = models.URLField(max_length=1000)
    unit = models.CharField(max_length=50, blank=True, default='')
    location = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tokopedia_products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} - Rp{self.price}"


class PriceAnomaly(models.Model):
    """Model to store detected price anomalies for review"""
    
    # Vendor source choices
    VENDOR_CHOICES = [
        ('gemilang', 'Gemilang'),
        ('mitra10', 'Mitra10'),
        ('tokopedia', 'Tokopedia'),
        ('depobangunan', 'Depo Bangunan'),
        ('juragan_material', 'Juragan Material'),
    ]
    
    # Review status choices
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('applied', 'Applied to Database'),
    ]
    
    vendor = models.CharField(max_length=50, choices=VENDOR_CHOICES)
    product_name = models.CharField(max_length=500)
    product_url = models.URLField(max_length=1000)
    unit = models.CharField(max_length=50)
    location = models.CharField(max_length=200, blank=True, default='')
    
    old_price = models.IntegerField(validators=[MinValueValidator(0)])
    new_price = models.IntegerField(validators=[MinValueValidator(0)])
    change_percent = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    detected_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    
    class Meta:
        db_table = 'price_anomalies'
        indexes = [
            models.Index(fields=['vendor']),
            models.Index(fields=['status']),
            models.Index(fields=['detected_at']),
            models.Index(fields=['product_name']),
        ]
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"{self.vendor} - {self.product_name} ({self.change_percent}% change)"
    
    @property
    def is_price_increase(self):
        """Check if anomaly is a price increase"""
        return self.new_price > self.old_price
    
    @property
    def price_difference(self):
        """Get absolute price difference"""
        return abs(self.new_price - self.old_price)