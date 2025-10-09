from django.db import models


class ScrapingVendorData(models.Model):
    """
    Model to store scraped vendor data with product information.
    """
    id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255, help_text="Name of the product")
    price = models.CharField(max_length=255, help_text="Price of the product")
    unit = models.CharField(max_length=255, help_text="Unit of measurement")
    vendor = models.CharField(max_length=255, help_text="Vendor name")
    location = models.CharField(max_length=255, help_text="Location where the product is available")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scraping_vendor_data'
        verbose_name = 'Scraping Vendor Data'
        verbose_name_plural = 'Scraping Vendor Data'

    def __str__(self):
        return f"{self.product_name} - {self.vendor} ({self.location})"