from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    
    # Secure validation endpoints (with CSRF protection)
    path('validate-input/', views.validate_scraper_input, name='validate_scraper_input'),
    path('validate-input-json/', views.validate_scraper_input_json, name='validate_scraper_input_json'),
    path('validate-input-api/', views.validate_scraper_input_api, name='validate_scraper_input_api'),
    
    # Legacy CSRF-exempt endpoint (use only when necessary)
    path('validate-input-legacy/', views.validate_scraper_input_legacy_api, name='validate_scraper_input_legacy_api'),
    
    # CSRF token endpoint for API clients
    path('csrf-token/', views.get_csrf_token, name='get_csrf_token'),
    
    path('validate/<str:vendor>/', views.validate_vendor_input, name='validate_vendor_input'),
    
    path('validate-params/', views.validate_scraping_params_endpoint, name='validate_params'),
    
    path('validation-rules/', views.get_validation_rules, name='validation_rules'),
    path('vendors/', views.get_supported_vendors, name='supported_vendors'),
]