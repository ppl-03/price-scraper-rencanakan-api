from django.urls import path
from .views import ScrapingVendorDataView

app_name = 'scraping_vendor_data'

urlpatterns = [
    path('', ScrapingVendorDataView.as_view(), name='scraping_vendor_data_list'),
    path('<int:vendor_data_id>/', ScrapingVendorDataView.as_view(), name='scraping_vendor_data_detail'),
]