from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    
    path('validate-input/', views.validate_scraper_input, name='validate_scraper_input'),
    path('validate-input-json/', views.validate_scraper_input_json, name='validate_scraper_input_json'),
    path('validate-input-api/', views.validate_scraper_input_api, name='validate_scraper_input_api'),
    
    path('validate/<str:vendor>/', views.validate_vendor_input, name='validate_vendor_input'),
    
    path('validate-params/', views.validate_scraping_params_endpoint, name='validate_params'),
    
    path('validation-rules/', views.get_validation_rules, name='validation_rules'),
    path('vendors/', views.get_supported_vendors, name='supported_vendors'),
]