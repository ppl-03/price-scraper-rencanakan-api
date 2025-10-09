from django.contrib import admin
from .models import ScrapingVendorData


@admin.register(ScrapingVendorData)
class ScrapingVendorDataAdmin(admin.ModelAdmin):
    """Admin interface for Scraping Vendor Data."""
    
    list_display = ('id', 'product_name', 'vendor', 'location', 'price', 'unit', 'created_at')
    list_filter = ('vendor', 'location', 'unit', 'created_at')
    search_fields = ('product_name', 'vendor', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product_name', 'price', 'unit')
        }),
        ('Vendor Information', {
            'fields': ('vendor', 'location')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )